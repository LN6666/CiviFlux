from __future__ import annotations

import math
import os
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Iterable, get_args

from defusedxml import ElementTree as SafeET
from urbanimpact.contracts import CityPack, Scenario, VehicleClass
from urbanimpact.network import Router, compile_restrictions
from urbanimpact.util import atomic_json, digest, file_hash

PINNED_SUMO_VERSION = "1.27.1"


class SimulationFailure(RuntimeError):
    def __init__(self, status: str, message: str):
        self.status = status
        super().__init__(message)


@dataclass(frozen=True)
class Demand:
    id: str
    edge_ids: tuple[str, ...]
    vehicle_class: str = "passenger"
    depart_s: float = 0.0


@dataclass(frozen=True)
class Limits:
    duration_s: float = 300.0
    wallclock_s: float = 60.0
    max_vehicles: int = 1000
    max_output_bytes: int = 50_000_000
    step_length_s: float = 1.0

    def __post_init__(self):
        if not (
            0 < self.duration_s <= 86400
            and 0 < self.wallclock_s <= 600
            and 0 < self.max_vehicles <= 10000
            and 1000 <= self.max_output_bytes <= 1_000_000_000
            and 0.01 <= self.step_length_s <= 1
        ):
            raise ValueError("Invalid bounded SUMO limits")


def _binary(name: str) -> str:
    found = Path(sys.executable).parent / name
    path = str(found) if found.is_file() else shutil.which(name)
    if not path:
        raise SimulationFailure("BLOCKED_ENVIRONMENT", f"Missing local executable: {name}")
    return path


def _kill_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    # Kill remaining descendants even if their wrapper already exited.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=3)


def _run_bounded(
    command: list[str], folder: Path, name: str, limits: Limits, cancel: Event | None = None
) -> dict:
    """Only called with adapter-owned executable arrays; never shells or user commands."""
    if cancel and cancel.is_set():
        raise SimulationFailure("CANCELLED", "Simulation cancelled before launch")
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / f"{name}.log"
    started = time.monotonic()
    with log.open("wb") as stream:
        process = subprocess.Popen(
            command, cwd=folder, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True, shell=False
        )
        try:
            while process.poll() is None:
                if cancel and cancel.is_set():
                    raise SimulationFailure("CANCELLED", "Simulation cancelled")
                if time.monotonic() - started > limits.wallclock_s:
                    raise SimulationFailure("RESOURCE_LIMIT", "SUMO wallclock limit exceeded")
                if sum(p.stat().st_size for p in folder.rglob("*") if p.is_file()) > limits.max_output_bytes:
                    raise SimulationFailure("RESOURCE_LIMIT", "SUMO output-size limit exceeded")
                time.sleep(0.05)
        except BaseException:
            _kill_group(process)
            raise
    text = log.read_text(errors="replace")
    if sum(p.stat().st_size for p in folder.rglob("*") if p.is_file()) > limits.max_output_bytes:
        raise SimulationFailure("RESOURCE_LIMIT", "SUMO output-size limit exceeded")
    if process.returncode != 0 or any(line.startswith("Error:") for line in text.splitlines()):
        raise SimulationFailure("FAILED", f"{name} failed with exit {process.returncode}; see {log}")
    return dict(
        command=command,
        exit_code=process.returncode,
        log=log.name,
        log_sha256=file_hash(log),
        wallclock_s=time.monotonic() - started,
    )


def _xml(path: Path, root: ET.Element) -> None:
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def synthetic_demand(
    city: CityPack, scenario: Scenario, vehicle_class: str = "passenger", max_vehicles: int = 20
) -> tuple[Demand, ...]:
    """Deterministic OD selection; explicitly synthetic, without modifying city demand."""
    result = Router().compare(city, scenario, vehicle_class)
    return tuple(
        Demand(f"synthetic-{i}", tuple(r["baseline"]["edge_ids"]), vehicle_class, float(i * 5))
        for i, r in enumerate(r for r in result["od"] if len(r["baseline"]["edge_ids"]) >= 2)
        if i < max_vehicles
    )


class SumoAdapter:
    def __init__(self):
        self.sumo = _binary("sumo")
        self.netconvert = _binary("netconvert")

    def _network(
        self, city: CityPack, folder: Path, limits: Limits, cancel: Event | None
    ) -> tuple[dict, dict]:
        mapping = {edge.id: f"e{i}" for i, edge in enumerate(sorted(city.edges, key=lambda e: e.id))}
        nmap = {node.id: f"n{i}" for i, node in enumerate(sorted(city.nodes, key=lambda n: n.id))}
        nodes = ET.Element("nodes")
        # Small-area local projection. Original physical edge lengths are preserved explicitly.
        lon0 = sum(n.lon for n in city.nodes) / len(city.nodes)
        lat0 = sum(n.lat for n in city.nodes) / len(city.nodes)
        for node in city.nodes:
            x = math.radians(node.lon - lon0) * 6371008.8 * math.cos(math.radians(lat0))
            y = math.radians(node.lat - lat0) * 6371008.8
            ET.SubElement(nodes, "node", id=nmap[node.id], x=str(x), y=str(y), type="priority")
        edges = ET.Element("edges")
        for edge in city.edges:
            attrs = dict(
                id=mapping[edge.id],
                **{"from": nmap[edge.source]},
                to=nmap[edge.target],
                numLanes="1",
                speed=str(edge.speed_kph / 3.6),
                length=str(edge.length_m),
                priority="1",
            )
            if edge.allowed_vehicle_classes:
                attrs["allow"] = " ".join(sorted(edge.allowed_vehicle_classes))
            else:
                attrs["disallow"] = "all"
            ET.SubElement(edges, "edge", attrs)
        _xml(folder / "nodes.nod.xml", nodes)
        _xml(folder / "edges.edg.xml", edges)
        command = [
            self.netconvert,
            "--node-files",
            "nodes.nod.xml",
            "--edge-files",
            "edges.edg.xml",
            "--output-file",
            "network.net.xml",
            "--no-turnarounds",
            "false",
            "--junctions.corner-detail",
            "0",
        ]
        if city.connections is not None:
            connections = ET.Element("connections")
            # Remove all topological turns outside the imported allowlist.
            by_source = {}
            for edge in city.edges:
                by_source.setdefault(edge.source, []).append(edge)
            permitted = {(c.from_edge, c.to_edge) for c in city.connections if c.allowed_vehicle_classes}
            for edge in city.edges:
                for target in by_source.get(edge.target, []):
                    if (edge.id, target.id) not in permitted:
                        ET.SubElement(
                            connections, "delete", **{"from": mapping[edge.id]}, to=mapping[target.id]
                        )
            for c in city.connections:
                if c.allowed_vehicle_classes:
                    ET.SubElement(
                        connections,
                        "connection",
                        **{"from": mapping[c.from_edge]},
                        to=mapping[c.to_edge],
                        fromLane="0",
                        toLane="0",
                        allow=" ".join(c.allowed_vehicle_classes),
                    )
            _xml(folder / "connections.con.xml", connections)
            command += ["--connection-files", "connections.con.xml"]
        invocation = _run_bounded(command, folder, "netconvert", limits, cancel)
        return mapping, invocation

    @staticmethod
    def _demand(
        city: CityPack, demands: tuple[Demand, ...], mapping: dict, folder: Path, limits: Limits
    ) -> None:
        if not demands or len(demands) > limits.max_vehicles:
            raise ValueError("Nonempty demand must fit max_vehicles limit")
        if len({d.id for d in demands}) != len(demands):
            raise ValueError("Duplicate demand vehicle IDs")
        edges = {e.id: e for e in city.edges}
        turns = None if city.connections is None else {(c.from_edge, c.to_edge): c for c in city.connections}
        routes = ET.Element("routes")
        for cls in sorted({d.vehicle_class for d in demands}):
            if cls not in get_args(VehicleClass) or cls == "pedestrian":
                raise ValueError("Unknown or unsupported SUMO vehicle class")
            t = ET.SubElement(
                routes,
                "vType",
                id=f"type-{cls}",
                vClass=cls,
                carFollowModel="Krauss",
                sigma="0",
                speedFactor="1",
                speedDev="0",
            )
            ET.SubElement(t, "param", key="device.rerouting.mode", value="8")
        for d in sorted(demands, key=lambda d: (d.depart_s, d.id)):
            if not math.isfinite(d.depart_s) or not 0 <= d.depart_s < limits.duration_s:
                raise ValueError("Departure outside bounded simulation")
            if not d.edge_ids or any(e not in edges for e in d.edge_ids):
                raise ValueError("Invalid demand edge IDs")
            if any(d.vehicle_class not in edges[e].allowed_vehicle_classes for e in d.edge_ids):
                raise ValueError("Demand violates imported road permissions")
            for a, b in zip(d.edge_ids, d.edge_ids[1:]):
                if edges[a].target != edges[b].source or (
                    turns is not None
                    and ((a, b) not in turns or d.vehicle_class not in turns[a, b].allowed_vehicle_classes)
                ):
                    raise ValueError("Disconnected or prohibited demand turn")
            v = ET.SubElement(
                routes,
                "vehicle",
                id=d.id,
                type=f"type-{d.vehicle_class}",
                depart=str(d.depart_s),
                departLane="best",
                departSpeed="0",
            )
            ET.SubElement(v, "route", edges=" ".join(mapping[e] for e in d.edge_ids))
        _xml(folder / "demand.rou.xml", routes)

    @staticmethod
    def _closures(
        city: CityPack, scenario: Scenario, mapping: dict, duration: float, folder: Path
    ) -> list[dict]:
        intervals = []
        relevant = []
        for r in scenario.restrictions:
            begin = max(0.0, (r.valid_from - scenario.window.start).total_seconds())
            end = min(duration, (r.valid_to - scenario.window.start).total_seconds())
            if begin < end:
                relevant.append((begin, end, r))
        boundaries = sorted({x for begin, end, _ in relevant for x in (begin, end)})
        additional = ET.Element("additional")
        if boundaries:
            rerouter = ET.SubElement(
                additional,
                "rerouter",
                id="all-closures",
                edges=" ".join(sorted(mapping.values())),
                probability="1",
            )
            edges = {e.id: e for e in city.edges}
            for begin, end in zip(boundaries, boundaries[1:]):
                blocked = {}
                for start, stop, r in relevant:
                    if start <= begin < stop:
                        for eid in r.edge_ids:
                            blocked.setdefault(eid, set()).update(r.blocked_classes)
                if not blocked:
                    continue
                interval = ET.SubElement(rerouter, "interval", begin=str(begin), end=str(end))
                for eid, classes in sorted(blocked.items()):
                    allowed = set(edges[eid].allowed_vehicle_classes) - classes
                    attrs = {"id": mapping[eid]}
                    attrs.update({"allow": " ".join(sorted(allowed))} if allowed else {"disallow": "all"})
                    ET.SubElement(interval, "closingReroute", attrs)
                intervals.append(
                    dict(begin_s=begin, end_s=end, blocked={e: sorted(c) for e, c in blocked.items()})
                )
        _xml(folder / "event.add.xml", additional)
        _xml(folder / "baseline.add.xml", ET.Element("additional"))
        return intervals

    @staticmethod
    def _parse(folder: Path, name: str, demands: tuple[Demand, ...], mapping: dict) -> dict:
        trips = SafeET.parse(folder / f"{name}.tripinfo.xml").getroot().findall("tripinfo")
        rows = []
        for trip in trips:
            finished = float(trip.attrib["arrival"]) >= 0
            rows.append(
                dict(
                    vehicle_id=trip.attrib["id"],
                    status="arrived" if finished else "unfinished",
                    duration_s=float(trip.attrib["duration"]) if finished else None,
                    distance_m=float(trip.attrib["routeLength"]),
                    depart_s=float(trip.attrib["depart"]),
                )
            )
        arrived = sum(r["status"] == "arrived" for r in rows)
        departed = sum(r["depart_s"] >= 0 for r in rows)
        summary = SafeET.parse(folder / f"{name}.summary.xml").getroot().findall("step")
        last = summary[-1].attrib if summary else {}
        teleported = int(float(last.get("teleports", "0")))
        rejected = int(float(last.get("discarded", "0")))
        collisions = int(float(last.get("collisions", "0")))
        if collisions:
            raise SimulationFailure("FAILED", "SUMO reported a collision; result cannot be published")
        departed = int(float(last.get("inserted", departed)))
        reverse = {v: k for k, v in mapping.items()}
        routes = {}
        for v in SafeET.parse(folder / f"{name}.routes.xml").getroot().findall("vehicle"):
            candidates = v.findall("route") or v.findall("routeDistribution/route")
            route = candidates[-1] if candidates else None
            routes[v.attrib["id"]] = dict(
                edges=[reverse.get(e, e) for e in route.attrib.get("edges", "").split()]
                if route is not None
                else [],
                exit_times_s=[float(s) for s in route.attrib.get("exitTimes", "").split()]
                if route is not None
                else [],
                arrival_s=float(v.attrib.get("arrival", "-1")),
            )
        durations = [r["duration_s"] for r in rows if r["duration_s"] is not None]
        # Denominator includes every requested vehicle, even if never inserted.
        return dict(
            demand_total=len(demands),
            arrived=arrived,
            unfinished=len(demands) - arrived,
            departed=departed,
            pending_departures=len(demands) - departed,
            teleported=teleported,
            rejected_departures=rejected,
            rejected_departures_basis="SUMO summary discarded count; input/route errors fail the run",
            collisions=collisions,
            mean_arrived_duration_s=sum(durations) / len(durations) if durations else None,
            mean_denominator=arrived,
            rows=rows,
            routes=routes,
            metrics_sha256=digest(
                dict(rows=rows, routes=routes, arrived=arrived, unfinished=len(demands) - arrived)
            ),
            scope="SYNTHETIC_DEMAND_WHATIF; duration mean conditional on arrival",
        )

    def run_pair(
        self,
        city: CityPack,
        scenario: Scenario,
        demands: Iterable[Demand],
        output_dir: Path,
        limits: Limits | None = None,
        cancel_event: Event | None = None,
        seed: int = 42,
    ) -> dict:
        limits = limits or Limits()
        demands = tuple(demands)
        if not demands or len(demands) > limits.max_vehicles:
            raise ValueError("Nonempty demand must fit max_vehicles limit")
        if not isinstance(seed, int) or not 0 <= seed <= 2**31 - 1:
            raise ValueError("Invalid random seed")
        compile_restrictions(city, scenario)
        duration = (scenario.window.end - scenario.window.start).total_seconds()
        if limits.duration_s > duration:
            raise ValueError("Simulation duration exceeds declared scenario window")
        folder = Path(output_dir).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        if any(folder.iterdir()):
            raise ValueError("SUMO output directory must be empty to preserve prior evidence")
        invocations = []
        try:
            atomic_json(folder / "citypack.json", city)
            atomic_json(folder / "scenario.json", scenario)
            atomic_json(folder / "demand.json", [vars(d) for d in demands])
            for name, binary in (("sumo-version", self.sumo), ("netconvert-version", self.netconvert)):
                invocations.append(_run_bounded([binary, "--version"], folder, name, limits, cancel_event))
                if f" {PINNED_SUMO_VERSION}\n" not in (folder / f"{name}.log").read_text():
                    raise SimulationFailure(
                        "BLOCKED_ENVIRONMENT", f"Require pinned SUMO {PINNED_SUMO_VERSION}"
                    )
            mapping, invocation = self._network(city, folder, limits, cancel_event)
            invocations.append(invocation)
            self._demand(city, demands, mapping, folder, limits)
            intervals = self._closures(city, scenario, mapping, limits.duration_s, folder)
            results = {}
            for stage in ("baseline", "event"):
                command = [
                    self.sumo,
                    "--net-file",
                    "network.net.xml",
                    "--route-files",
                    "demand.rou.xml",
                    "--additional-files",
                    f"{stage}.add.xml",
                    "--seed",
                    str(seed),
                    "--begin",
                    "0",
                    "--end",
                    str(limits.duration_s),
                    "--step-length",
                    str(limits.step_length_s),
                    "--time-to-teleport",
                    "-1",
                    "--collision.action",
                    "warn",
                    "--device.rerouting.probability",
                    "1",
                    "--device.rerouting.mode",
                    "8",
                    "--device.rerouting.period",
                    "0",
                    "--no-step-log",
                    "true",
                    "--tripinfo-output",
                    f"{stage}.tripinfo.xml",
                    "--tripinfo-output.write-unfinished",
                    "true",
                    "--vehroute-output",
                    f"{stage}.routes.xml",
                    "--vehroute-output.exit-times",
                    "true",
                    "--vehroute-output.last-route",
                    "true",
                    "--vehroute-output.write-unfinished",
                    "true",
                    "--summary-output",
                    f"{stage}.summary.xml",
                ]
                invocations.append(_run_bounded(command, folder, stage, limits, cancel_event))
                results[stage] = self._parse(folder, stage, demands, mapping)
            report = dict(
                status="PASS",
                simulation_status="completed",
                engine="real_local_sumo",
                sumo_version=PINNED_SUMO_VERSION,
                demand_kind="synthetic",
                validation="SYNTHETIC_DEMAND_WHATIF",
                network_temporality=city.network_temporality,
                citypack_id=city.citypack_id,
                scenario_id=scenario.scenario_id,
                source_snapshot_hash=digest(city),
                scenario_hash=digest(scenario),
                simulation_start=scenario.window.start.isoformat(),
                seed=seed,
                network_sha256=file_hash(folder / "network.net.xml"),
                demand_sha256=file_hash(folder / "demand.rou.xml"),
                edge_mapping=mapping,
                closure_intervals=intervals,
                baseline=results["baseline"],
                event=results["event"],
                limits=vars(limits),
                commands=invocations,
                assumptions=[
                    "Single lane per imported directed edge; no inferred traffic signal phases.",
                    "Local equirectangular projection; original edge lengths and speed limits retained.",
                    "Krauss car following, sigma=0, speedFactor=1; 100% rerouter knowledge.",
                    "Mode 8 with exactly one concurrent rerouter; teleport disabled; no warmup.",
                    "Fixed routes share identical demand and seed. No measured OD calibration.",
                ],
                artifacts={p.name: file_hash(p) for p in folder.iterdir() if p.is_file()},
            )
            atomic_json(folder / "sumo_pair.json", report)
            return report
        except BaseException as error:
            atomic_json(
                folder / "failure.json",
                dict(status=getattr(error, "status", "FAILED"), error=str(error), commands=invocations),
            )
            raise
