"""Explore active-mode corridor sensitivity without inferring an event closure.

This uses a typed, replayable assumed restriction. The BCC notice binds only
the motor-road geometry; it does not assert any pedestrian/bicycle closure.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from pyproj import Transformer
from shapely.geometry import LineString
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "core"), str(ROOT)]

from urbanimpact.actions import Workspace
from urbanimpact.citypack.fetch import sha256_file
from urbanimpact.contracts import ActionRequest, CityPack, Scenario
from urbanimpact.network import ACTIVE_MODE_SPEED_MPS, Router, compile_restrictions
from urbanimpact.util import digest

CASE = Path("data/event_cases/baku-f1-2026-active-indirect-case.json")
BUS_CASE = Path("data/event_cases/baku-f1-2026-indirect-plan-case.json")
MOTOR_CITY = Path("data/citypacks/baku-f1-2026/citypack.json")
MULTIMODAL_CITY = Path("data/citypacks/baku-f1-2026-multimodal/citypack.json")
SUMMARY = Path("evidence/events/baku-2026-active-indirect-probe.json")
MAP = Path("web/public/validation/baku-active-indirect.json")
MOTOR_CLASSES = frozenset(
    {"passenger", "bus", "emergency", "delivery", "truck", "taxi", "motorcycle"}
)
PROJECT = Transformer.from_crs("EPSG:4326", "EPSG:32639", always_xy=True).transform


def _mean(edge) -> tuple[float, float]:
    return tuple(sum(p[i] for p in edge.geometry) / len(edge.geometry) for i in (0, 1))


def _within(point, bbox) -> bool:
    return bbox[0] <= point[0] <= bbox[2] and bbox[1] <= point[1] <= bbox[3]


def corridor_candidates(city: CityPack, motor_edges: list, buffer_m: float) -> list:
    """Find imported lines crossing a declared metric buffer around mapped roads."""
    if not 0 < buffer_m <= 30 or not motor_edges:
        raise ValueError("Buffer must be in (0, 30] metres with input roads")
    geometry = unary_union(
        [transform(PROJECT, LineString(edge.geometry)) for edge in motor_edges]
    ).buffer(buffer_m)
    lonlat = [p for edge in motor_edges for p in edge.geometry]
    bounds = (
        min(p[0] for p in lonlat) - 0.002,
        min(p[1] for p in lonlat) - 0.002,
        max(p[0] for p in lonlat) + 0.002,
        max(p[1] for p in lonlat) + 0.002,
    )
    selected = []
    for edge in city.edges:
        if len(edge.geometry) < 2:
            continue
        edge_bounds = LineString(edge.geometry).bounds
        if (
            edge_bounds[2] < bounds[0]
            or edge_bounds[0] > bounds[2]
            or edge_bounds[3] < bounds[1]
            or edge_bounds[1] > bounds[3]
        ):
            continue
        if transform(PROJECT, LineString(edge.geometry)).intersects(geometry):
            selected.append(edge)
    return sorted(selected, key=lambda edge: edge.id)


def _nearest(nodes: list, coordinate: list[float]) -> tuple[str, float]:
    lon, lat = coordinate
    node = min(nodes, key=lambda n: ((n.lon - lon) * 0.76) ** 2 + (n.lat - lat) ** 2)
    gap = (((node.lon - lon) * 84600) ** 2 + ((node.lat - lat) * 111130) ** 2) ** 0.5
    return node.id, round(gap, 1)


def _feature(edge, layer: str, buffer_m: float) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": edge.geometry},
        "properties": {
            "id": edge.id,
            "name": edge.name,
            "layer": layer,
            "source_id": edge.source_id,
            "buffer_m": buffer_m,
            "evidence_status": "HYPOTHETICAL_EXPOSURE_NOT_OBSERVED_CLOSURE",
        },
    }


def _collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def _action_scenario(city: CityPack, mode: str, blocked: list[str], card: dict, label: str):
    sid = f"baku-active-{mode}-{label}"
    restriction = {
        "id": f"assumed-{mode}-{label}",
        "edge_ids": blocked,
        "valid_from": card["window_start"],
        "valid_to": card["window_end"],
        "blocked_classes": [mode],
        "evidence_kind": "assumed",
        "evidence_refs": ["ASSUMED-ACTIVE-CORRIDOR"],
    }
    base = Scenario.model_validate(
        {
            "scenario_id": sid,
            "citypack_id": city.citypack_id,
            "kind": "road",
            "timezone": "Asia/Baku",
            "analysis_at": card["analysis_at"],
            "window": {"start": card["window_start"], "end": card["window_end"]},
            "objective": "road_disruption",
            "analysis_vehicle_class": mode,
            "seed_spec": {"entity_ids": [blocked[0]]},
            "assumptions": [
                {
                    "id": "active-corridor-hypothesis",
                    "description": card["restriction_assumption"],
                    "affects": [mode, "route_connectivity", "fixed_speed_travel_time"],
                }
            ],
        }
    )
    timestamp = datetime.fromisoformat(card["analysis_at"])
    with TemporaryDirectory(prefix="civiflux-active-") as temp:
        base_path = Path(temp)
        workspace = Workspace(base_path / "workspace.sqlite", city)
        create = ActionRequest(
            action_id=sid + "-create",
            action_type="CreateScenario",
            scenario_id=sid,
            parameters={"scenario": base.model_dump(mode="json")},
            actor_context="reproducible-user-requested-sensitivity",
        )
        add = ActionRequest(
            action_id=sid + "-restriction",
            action_type="AddRoadRestriction",
            scenario_id=sid,
            parameters={"restriction": restriction},
            expected_overlay_hash=digest(base),
            actor_context="reproducible-user-requested-sensitivity",
        )
        records = [workspace.commit(request, timestamp=timestamp) for request in (create, add)]
        scenario = workspace.scenario(sid)
        replay = workspace.replay(sid, base_path / "replayed.sqlite")
        assert digest(replay.scenario(sid)) == digest(scenario)
    compiled = compile_restrictions(city, scenario, mode)
    if compiled != frozenset(blocked):
        raise ValueError("Action restriction did not match candidate edges")
    return scenario, records


def build(root: Path = ROOT) -> dict:
    card = json.loads((root / CASE).read_text())
    bus_case = json.loads((root / BUS_CASE).read_text())
    if card["source_case"] != BUS_CASE.as_posix() or card["modes"] != ["pedestrian", "bicycle"]:
        raise ValueError("Active-mode case contract changed")
    if card["speed_assumptions_mps"] != ACTIVE_MODE_SPEED_MPS:
        raise ValueError("Active-mode cost policy changed")
    if [float(x) for x in card["corridor_buffer_m"]] != [0.2, 15.0]:
        raise ValueError("Exploratory buffer sensitivity contract changed")
    motor_path, multi_path = root / MOTOR_CITY, root / MULTIMODAL_CITY
    if (
        sha256_file(motor_path) != bus_case["citypack_sha256"]
        or sha256_file(multi_path) != bus_case["multimodal_citypack_sha256"]
    ):
        raise ValueError("Source CityPack bytes changed")
    motor = CityPack.model_validate_json(motor_path.read_bytes())
    city = CityPack.model_validate_json(multi_path.read_bytes())
    if motor.sources[0].sha256 != city.sources[0].sha256:
        raise ValueError("Motor and active networks use different OSM source snapshots")
    closure = bus_case["closure_input"]
    source_html = root / "data/raw/baku-f1-2026-circuit-traffic.html"
    if sha256_file(source_html) != closure["source_sha256"]:
        raise ValueError("BCC source bytes changed")
    road_candidates = sorted(
        (
            edge
            for edge in motor.edges
            if edge.name == closure["street_name_in_citypack"]
            and "bus" in edge.allowed_vehicle_classes
            and _within(_mean(edge), closure["midpoint_bbox"])
        ),
        key=lambda edge: edge.id,
    )
    if len(road_candidates) != 12:
        raise ValueError("BCC mapped road subset changed")
    edges = {edge.id: edge for edge in city.edges}
    output = {
        "schema_version": "civiflux-active-indirect-v1",
        "status": "HYPOTHETICAL_INDIRECT_STRESS_TEST",
        "case_id": card["case_id"],
        "source_osm_sha256": city.sources[0].sha256,
        "motor_citypack_sha256": sha256_file(motor_path),
        "multimodal_citypack_sha256": sha256_file(multi_path),
        "bcc_notice_sha256": sha256_file(source_html),
        "active_case_sha256": sha256_file(root / CASE),
        "bus_case_sha256": sha256_file(root / BUS_CASE),
        "source_motor_candidate_edges": len(road_candidates),
        "condition": card["restriction_assumption"],
        "origin_target_policy": card["origin_target_policy"],
        "speed_assumptions_mps": card["speed_assumptions_mps"],
        "pedestrian_area_routing": "NOT_MODELLED",
        "buffer_results": [],
        "claim_ceiling": card["claim_ceiling"],
    }
    map_layers: dict[str, dict] = {}
    for buffer_m, label in ((0.2, "colocated"), (15.0, "15m")):
        exposed = corridor_candidates(city, road_candidates, buffer_m)
        record = {"buffer_m": buffer_m, "modes": {}}
        for mode in card["modes"]:
            affected = [edge for edge in exposed if mode in edge.allowed_vehicle_classes]
            if not affected:
                raise ValueError(f"No {mode} candidate links in declared sensitivity geometry")
            blocked = [edge.id for edge in affected]
            scenario, actions = _action_scenario(city, mode, blocked, card, label)
            usable = {e.source for e in city.edges if mode in e.allowed_vehicle_classes} & {
                e.target for e in city.edges if mode in e.allowed_vehicle_classes
            }
            nodes = [node for node in city.nodes if node.id in usable]
            index = Router._index(city, mode)
            od_results = []
            baseline_ids = set()
            for pair in bus_case["synthetic_od_pairs"]:
                origin, origin_gap = _nearest(nodes, pair["start_lon_lat"])
                target, target_gap = _nearest(nodes, pair["end_lon_lat"])
                baseline = Router._search(index, origin, [target], ())[target]
                conditional = Router._search(index, origin, [target], blocked)[target]
                baseline_ids.update(baseline["edge_ids"])
                comparable = baseline["reachable"] and conditional["reachable"]
                od_results.append(
                    {
                        "id": pair["id"],
                        "synthetic": True,
                        "origin_node": origin,
                        "target_node": target,
                        "origin_snap_gap_m": origin_gap,
                        "target_snap_gap_m": target_gap,
                        "baseline_status": baseline["status"],
                        "conditional_status": conditional["status"],
                        "baseline_distance_m": baseline["distance_m"],
                        "conditional_distance_m": conditional["distance_m"],
                        "baseline_assumed_freeflow_s": baseline["travel_time_s"],
                        "conditional_assumed_freeflow_s": conditional["travel_time_s"],
                        "delta_distance_m": round(
                            conditional["distance_m"] - baseline["distance_m"], 1
                        )
                        if comparable
                        else None,
                        "delta_assumed_freeflow_s": round(
                            conditional["travel_time_s"] - baseline["travel_time_s"], 1
                        )
                        if comparable
                        else None,
                        "baseline_uses_exposed_edges": len(set(baseline["edge_ids"]) & set(blocked)),
                    }
                )
            dedicated = [e for e in affected if not set(e.allowed_vehicle_classes) & MOTOR_CLASSES]
            record["modes"][mode] = {
                "exposed_directed_edges": len(affected),
                "exposed_dedicated_nonmotor_edges": len(dedicated),
                "sum_directed_length_m": round(sum(e.length_m for e in affected), 1),
                "baseline_reachable_od": sum(r["baseline_status"] == "available" for r in od_results),
                "conditional_reachable_od": sum(
                    r["conditional_status"] == "available" for r in od_results
                ),
                "od": od_results,
                "scenario_overlay_hash": digest(scenario),
                "action_records": [a["record"] for a in actions],
                "action_replay_verified": True,
            }
            if label == "15m":
                map_layers[mode + "_exposed_15m"] = _collection(
                    [_feature(edge, mode + "_hypothetical_exposure", buffer_m) for edge in affected]
                )
                map_layers[mode + "_baseline"] = _collection(
                    [_feature(edges[eid], mode + "_baseline", buffer_m) for eid in sorted(baseline_ids)]
                )
        output["buffer_results"].append(record)
    target = root / SUMMARY
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    public = {
        "schema_version": output["schema_version"],
        "status": output["status"],
        "case_id": output["case_id"],
        "summary": output,
        "layers": map_layers,
        "osm_attribution": "© OpenStreetMap contributors; ODbL 1.0; Geofabrik Azerbaijan 2026-09-18 extract",
        "interpretation": "Hypothetical 15 m corridor exposure and synthetic baseline paths; no actual active-mode closure or event impact inferred",
    }
    (root / MAP).write_text(json.dumps(public, ensure_ascii=False, separators=(",", ":")) + "\n")
    return output


if __name__ == "__main__":
    summary = build()
    print(json.dumps({"status": summary["status"], "buffer_results": summary["buffer_results"]}, ensure_ascii=False))
