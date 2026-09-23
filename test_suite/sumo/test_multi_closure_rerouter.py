"""Real SUMO proof fixture for the single-rerouter multiple-closure invariant.

The network has directed return edges, so a route loop is topologically possible.
Both closures are active for the same vehicle. The compiler must communicate
their joint state through one rerouter rather than independently switching
between closure-specific rerouters in SUMO's mode 8.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from defusedxml import ElementTree as SafeET
from urbanimpact.contracts import CityPack, Scenario
from urbanimpact.util import file_hash

from adapters.sumo import Demand, Limits, SumoAdapter
from adapters.sumo.adapter import _run_bounded

AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
EDGES = (
    ("sa", "S", "A", 100),
    ("ab", "A", "B", 100),
    ("bc", "B", "C", 200),
    ("ch", "C", "H", 100),
    ("ad", "A", "D", 120),
    ("de", "D", "E", 120),
    ("ec", "E", "C", 180),
    ("af", "A", "F", 120),
    ("fg", "F", "G", 120),
    ("gc", "G", "C", 180),
    ("da", "D", "A", 120),  # return arc: A -> D -> A
    ("eb", "E", "B", 180),  # return arc: A -> D -> E -> B
    ("ga", "G", "A", 180),  # return arc: A -> F -> G -> A
)


def cycle_fixture(reverse_restrictions: bool = False) -> tuple[CityPack, Scenario]:
    xy = {
        "S": (-100, 0),
        "A": (0, 0),
        "B": (100, 0),
        "C": (300, 0),
        "H": (400, 0),
        "D": (80, 120),
        "E": (200, 120),
        "F": (80, -120),
        "G": (200, -120),
    }
    city = CityPack.model_validate(
        dict(
            citypack_id="sumo-rerouter-cycle",
            network_temporality="synthetic",
            transit_temporality="unavailable",
            sources=[
                dict(
                    id="cycle-fixture",
                    url="synthetic:rerouter-cycle",
                    sha256="0" * 64,
                    retrieved_at=AT.isoformat(),
                    license="CC0",
                )
            ],
            nodes=[dict(id=n, lon=24 + x / 55600, lat=60 + y / 111200) for n, (x, y) in xy.items()],
            edges=[
                dict(
                    id=e,
                    source=a,
                    target=b,
                    length_m=length,
                    speed_kph=36,
                    allowed_vehicle_classes=["passenger"],
                    source_id="cycle-fixture",
                    external_id=e,
                )
                for e, a, b, length in EDGES
            ],
        )
    )
    restrictions = [
        dict(
            id=f"close-{edge}",
            edge_ids=[edge],
            blocked_classes=["passenger"],
            valid_from=AT,
            valid_to=AT + timedelta(seconds=300),
            evidence_kind="assumed",
            evidence_refs=["cycle-fixture"],
        )
        for edge in ("bc", "ec")
    ]
    if reverse_restrictions:
        restrictions.reverse()
    scenario = Scenario.model_validate(
        dict(
            scenario_id="simultaneous-closures-with-cycles",
            citypack_id=city.citypack_id,
            kind="road",
            analysis_at=AT,
            window=dict(start=AT, end=AT + timedelta(seconds=300)),
            seed_spec=dict(entity_ids=["S"]),
            restrictions=restrictions,
            assumptions=[
                dict(
                    id="synthetic-cycle-closures",
                    description="Two simultaneous assumed closures in a synthetic cyclic network",
                    affects=["restriction", "demand"],
                )
            ],
        )
    )
    return city, scenario


def run_cycle_pair(output_dir: Path, reverse_restrictions: bool = False) -> dict:
    city, scenario = cycle_fixture(reverse_restrictions)
    return SumoAdapter().run_pair(
        city,
        scenario,
        [Demand("vehicle", ("sa", "ab", "bc", "ch"))],
        output_dir,
        Limits(duration_s=300),
        seed=42,
    )


def assert_single_rerouter_loop_free(output_dir: Path, report: dict) -> dict:
    assert report["engine"] == "real_local_sumo"
    assert report["sumo_version"] == "1.27.1"
    assert report["status"] == "PASS"
    assert report["baseline"]["arrived"] == report["event"]["arrived"] == 1
    assert report["baseline"]["routes"]["vehicle"]["edges"] == ["sa", "ab", "bc", "ch"]
    assert report["event"]["routes"]["vehicle"]["edges"] == ["sa", "af", "fg", "gc", "ch"]
    assert report["baseline"]["teleported"] == report["event"]["teleported"] == 0
    assert report["event"]["unfinished"] == report["event"]["pending_departures"] == 0
    assert report["event"]["rejected_departures"] == report["event"]["collisions"] == 0
    assert report["closure_intervals"] == [
        {"begin_s": 0.0, "end_s": 300, "blocked": {"bc": ["passenger"], "ec": ["passenger"]}}
    ]
    route = report["event"]["routes"]["vehicle"]
    assert len(route["edges"]) == len(set(route["edges"]))  # no route cycle
    assert len(route["exit_times_s"]) == len(route["edges"])
    assert all(a < b for a, b in zip(route["exit_times_s"], route["exit_times_s"][1:]))
    assert route["arrival_s"] > 0
    assert all("--ignore-route-errors" not in c["command"] for c in report["commands"])

    # vehroute-output.last-route reports the final assigned route, which alone
    # cannot exclude earlier oscillation. Replay the exact pinned SUMO command
    # with floating-car trace output and inspect every edge the car occupied.
    event_command = next(
        c["command"] for c in report["commands"] if "event.add.xml" in c["command"]
    ).copy()
    for switch in ("--tripinfo-output", "--vehroute-output", "--summary-output"):
        event_command[event_command.index(switch) + 1] = (
            "trace." + event_command[event_command.index(switch) + 1]
        )
    event_command.extend(["--fcd-output", "trace.fcd.xml"])
    trace_invocation = _run_bounded(event_command, output_dir, "trace", Limits(duration_s=300))
    reverse = {native: eid for eid, native in report["edge_mapping"].items()}
    occupied = []
    for point in SafeET.parse(output_dir / "trace.fcd.xml").getroot().findall("timestep/vehicle"):
        if point.attrib["id"] != "vehicle":
            continue
        lane = point.attrib["lane"]
        native_edge = lane.rsplit("_", 1)[0]
        edge = reverse.get(native_edge)  # skip internal intersection lanes
        if edge and (not occupied or occupied[-1] != edge):
            occupied.append(edge)
    assert occupied == route["edges"]
    assert len(occupied) == len(set(occupied))  # the driven trajectory has no loop
    assert not {"bc", "ec"}.intersection(occupied)
    assert trace_invocation["exit_code"] == 0

    root = ET.parse(output_dir / "event.add.xml").getroot()
    rerouters = root.findall("rerouter")
    assert len(rerouters) == 1  # structural guarantee: no concurrent independent rerouters
    assert rerouters[0].attrib["id"] == "all-closures"
    assert rerouters[0].attrib["probability"] == "1"
    intervals = rerouters[0].findall("interval")
    assert len(intervals) == 1
    assert float(intervals[0].attrib["begin"]) == 0
    assert float(intervals[0].attrib["end"]) == 300
    closures = intervals[0].findall("closingReroute")
    assert len(closures) == 2
    assert {c.attrib["id"] for c in closures} == {
        report["edge_mapping"]["bc"],
        report["edge_mapping"]["ec"],
    }
    assert all(c.attrib.get("disallow") == "all" for c in closures)  # hard, never soft

    # The topology admits several directed cycles; a loop-free outcome alone
    # would be weak evidence if the fixture were acyclic.
    edge_pairs = {(a, b) for _, a, b, _ in EDGES}
    assert {("A", "D"), ("D", "A"), ("A", "F"), ("G", "A")} <= edge_pairs
    return {
        "assertion": "single merged rerouter on a loop-capable graph; both hard closures active",
        "compiled_rerouter_count": len(rerouters),
        "compiled_closure_count": len(closures),
        "loop_capable_return_edges": ["da", "eb", "ga"],
        "baseline_route": report["baseline"]["routes"]["vehicle"]["edges"],
        "event_route": route["edges"],
        "observed_trajectory_edges": occupied,
        "event_route_has_repeated_edge": False,
        "network_sha256": report["network_sha256"],
        "demand_sha256": report["demand_sha256"],
        "event_add_sha256": file_hash(output_dir / "event.add.xml"),
        "event_routes_sha256": file_hash(output_dir / "event.routes.xml"),
        "fcd_trace_sha256": file_hash(output_dir / "trace.fcd.xml"),
        "trace_command": trace_invocation,
        "sumo_pair_sha256": file_hash(output_dir / "sumo_pair.json"),
        "sumo_version": report["sumo_version"],
    }


@pytest.mark.sumo
def test_multiple_simultaneous_closures_on_cyclic_network_use_one_rerouter(tmp_path):
    first = run_cycle_pair(tmp_path / "first")
    assert_single_rerouter_loop_free(tmp_path / "first", first)
    reversed_order = run_cycle_pair(tmp_path / "reverse", reverse_restrictions=True)
    assert_single_rerouter_loop_free(tmp_path / "reverse", reversed_order)
    # netconvert embeds a generation timestamp in an XML comment, so its raw
    # file hash differs even when the effective network is identical.
    assert ET.tostring(ET.parse(tmp_path / "first" / "network.net.xml").getroot()) == ET.tostring(
        ET.parse(tmp_path / "reverse" / "network.net.xml").getroot()
    )
    assert file_hash(tmp_path / "first" / "edges.edg.xml") == file_hash(
        tmp_path / "reverse" / "edges.edg.xml"
    )
    assert first["demand_sha256"] == reversed_order["demand_sha256"]
    assert first["event"]["metrics_sha256"] == reversed_order["event"]["metrics_sha256"]
    assert file_hash(tmp_path / "first" / "event.add.xml") == file_hash(
        tmp_path / "reverse" / "event.add.xml"
    )
