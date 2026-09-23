#!/usr/bin/env python3
"""Rebuild a wider Helsinki road graph and compare the same candidate ODs.

This is a current-network crop-sensitivity check, not historical validation.
It reads only previously frozen local source bytes and never performs egress.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from collections import Counter
from pathlib import Path

from urbanimpact.citypack.fetch import sha256_file
from urbanimpact.contracts import CityPack, Scenario
from urbanimpact.network import compare_boundaries

from adapters.osm import convert_network, extract_roi

ROOT = Path(__file__).resolve().parents[1]
OUTER_BBOX = [24.9, 60.15, 25.025, 60.215]
CASES = ("road", "fire")


def _contains(inner_bbox: list[float], outer_bbox: list[float]) -> bool:
    return (
        outer_bbox[0] <= inner_bbox[0] < inner_bbox[2] <= outer_bbox[2]
        and outer_bbox[1] <= inner_bbox[1] < inner_bbox[3] <= outer_bbox[3]
    )


def _fixed_facilities(inner: CityPack, outer: CityPack) -> tuple[tuple, list[dict]]:
    """Freeze source facility and entrance identity, excluding unpaired targets."""
    outer_nodes = {node.id for node in outer.nodes}
    outer_facilities = {facility.id for facility in outer.facilities}
    selected = []
    excluded = []
    for facility in inner.facilities:
        reason = None
        if facility.id not in outer_facilities:
            reason = "facility absent in enlarged extraction"
        elif facility.entrance_node_id is None:
            reason = "candidate entrance unknown in inner crop"
        elif facility.entrance_node_id not in outer_nodes:
            reason = "inner candidate entrance node absent in enlarged graph"
        if reason:
            excluded.append({"facility_id": facility.id, "reason": reason})
        else:
            selected.append(facility)
    if not selected:
        raise ValueError("No fixed facility entrances are shared across crops")
    return tuple(selected), excluded


def _network_diagnostics(inner: CityPack, outer: CityPack) -> dict:
    """Expose graph changes introduced by a fresh conversion of the larger ROI."""
    inner_edges = {edge.id: edge for edge in inner.edges}
    outer_edges = {edge.id: edge for edge in outer.edges}
    shared_ids = inner_edges.keys() & outer_edges.keys()
    inner_turns = {(turn.from_edge, turn.to_edge): turn for turn in inner.connections or ()}
    outer_turns = {(turn.from_edge, turn.to_edge): turn for turn in outer.connections or ()}
    shared_turns = inner_turns.keys() & outer_turns.keys()
    return {
        "shared_edge_ids": len(shared_ids),
        "inner_edge_ids_absent_outer": len(inner_edges.keys() - outer_edges.keys()),
        "outer_edge_ids_absent_inner": len(outer_edges.keys() - inner_edges.keys()),
        "shared_edges_with_changed_endpoints": sum(
            (inner_edges[edge_id].source, inner_edges[edge_id].target)
            != (outer_edges[edge_id].source, outer_edges[edge_id].target)
            for edge_id in shared_ids
        ),
        "shared_edges_with_changed_travel_time": sum(
            abs(inner_edges[edge_id].travel_time_s - outer_edges[edge_id].travel_time_s) > 1e-9
            for edge_id in shared_ids
        ),
        "shared_turns": len(shared_turns),
        "inner_turns_absent_outer": len(inner_turns.keys() - outer_turns.keys()),
        "shared_turns_with_changed_permissions": sum(
            inner_turns[turn_id].allowed_vehicle_classes != outer_turns[turn_id].allowed_vehicle_classes
            for turn_id in shared_turns
        ),
    }


def _case_summary(root: Path, inner: CityPack, outer: CityPack, kind: str) -> dict:
    scenario = Scenario.model_validate_json((root / f"evidence/wp1/{kind}_scenario.json").read_bytes())
    if scenario.citypack_id != inner.citypack_id:
        raise ValueError(f"{kind} scenario does not match frozen inner citypack")
    inner_edges = {edge.id: edge for edge in inner.edges}
    outer_edges = {edge.id for edge in outer.edges}
    restrictions = {edge_id for restriction in scenario.restrictions for edge_id in restriction.edge_ids}
    if not restrictions <= outer_edges:
        raise ValueError(f"{kind} restrictions are not identical in the enlarged graph")
    seed = scenario.seed_spec.entity_ids[0]
    if seed not in inner_edges or seed not in outer_edges:
        raise ValueError(f"{kind} origin seed is not shared by both graphs")
    origin = inner_edges[seed].source
    if origin not in {node.id for node in outer.nodes}:
        raise ValueError(f"{kind} origin node is not shared by both graphs")

    fixed, excluded = _fixed_facilities(inner, outer)
    inner_fixed = inner.model_copy(update={"facilities": fixed})
    outer_fixed = outer.model_copy(update={"facilities": fixed})
    comparison = compare_boundaries(inner_fixed, outer_fixed, scenario, [origin], threshold_seconds=1.0)
    diffs = []
    for difference in comparison["differences"]:
        before, after = difference.get("inner"), difference.get("outer")
        diffs.append(
            {
                "facility_id": difference["facility_id"],
                "stage": difference.get("stage"),
                "reason": difference.get("reason", "status or time differs beyond threshold"),
                "inner_status": before["status"] if before else None,
                "outer_status": after["status"] if after else None,
                "inner_travel_time_s": before["travel_time_s"] if before else None,
                "outer_travel_time_s": after["travel_time_s"] if after else None,
            }
        )
    return {
        "kind": kind,
        "origin": origin,
        "origin_seed_edge": seed,
        "vehicle_class": "passenger",
        "restricted_edge_count": len(restrictions),
        "restricted_edges_shared": True,
        "fixed_od_count": len(fixed),
        "excluded_candidate_targets": excluded,
        "comparison_status": comparison["status"],
        "threshold_seconds": comparison["threshold_seconds"],
        "difference_count": len(diffs),
        "differences_by_stage": dict(Counter(d.get("stage") or "unpaired" for d in diffs)),
        "differences": diffs,
        "inner_network_hash": comparison["inner_network_hash"],
        "outer_network_hash": comparison["outer_network_hash"],
    }


def run(root: Path = ROOT, output: Path | None = None) -> dict:
    started = time.monotonic()
    inner_path = root / "data/citypacks/helsinki-current/citypack.json"
    raw_path = root / "data/raw/hsl.osm.pbf"
    inner = CityPack.model_validate_json(inner_path.read_bytes())
    inner_bbox = inner.evidence["bbox"]
    if not _contains(inner_bbox, OUTER_BBOX):
        raise ValueError("Declared outer crop does not contain the inner crop")
    osm_source = next(source for source in inner.sources if source.id == "S03-OSM")
    if sha256_file(raw_path) != osm_source.sha256:
        raise ValueError("Frozen OSM source hash differs from the inner citypack")
    netconvert = root / ".venv/bin/netconvert"
    version = subprocess.check_output([str(netconvert), "--version"], text=True).splitlines()[0]
    if version != "Eclipse SUMO netconvert 1.27.1":
        raise ValueError(f"Unexpected netconvert version: {version}")

    target_dir = root / "data/citypacks/helsinki-boundary-outer"
    target_dir.mkdir(parents=True, exist_ok=True)
    extraction = extract_roi(raw_path, target_dir / "outer.osm.xml", OUTER_BBOX)
    network = convert_network(
        target_dir / "outer.osm.xml",
        target_dir / "outer.net.xml",
        netconvert,
        target_dir / "netconvert.log",
        extraction,
    )
    inner_command = inner.evidence["network_converter"]["command"]
    outer_command = network["conversion"]["command"]
    if inner_command[5:] != outer_command[5:]:
        raise ValueError("Network conversion flags differ between the two crops")
    outer_data = inner.model_dump(mode="json")
    outer_data.update({key: network[key] for key in ("nodes", "edges", "connections", "facilities")})
    outer_data["citypack_id"] = "helsinki-boundary-outer-" + hashlib.sha256(
        json.dumps([osm_source.sha256, OUTER_BBOX, version], separators=(",", ":")).encode()
    ).hexdigest()[:12]
    outer_data["evidence"] = {
        **inner.evidence,
        "bbox": OUTER_BBOX,
        "scope": "enlarged current road network for fixed-OD boundary sensitivity only",
        "network_converter": network["conversion"],
        "osm_restriction_relations": extraction["restriction_relations"],
        "conditional_access_way_ids": extraction["conditional_tag_way_ids"],
        "sumo_network_path": str((target_dir / "outer.net.xml").relative_to(root)),
        "boundary_stability": "SCENARIO_SPECIFIC_COMPARISON_RECORDED_SEPARATELY",
    }
    outer_data["warnings"] = [
        *inner.warnings,
        "GTFS and facility identity are frozen from the inner snapshot for road-boundary comparison.",
    ]
    outer = CityPack.model_validate(outer_data)
    outer_path = target_dir / "citypack.json"
    outer_path.write_text(outer.model_dump_json() + "\n")

    report = {
        "status": "PASS_SCOPE_BOUNDARY_COMPARISON_EXECUTED",
        "claim_boundary": "Current OSM fixed-weight routing at selected origins and candidate entrances only; differences do not imply historical outcomes or citywide stability.",
        "source_sha256": osm_source.sha256,
        "source_license": "ODbL-1.0, © OpenStreetMap contributors; imported via HSL",
        "inner_citypack_id": inner.citypack_id,
        "inner_citypack_sha256": sha256_file(inner_path),
        "outer_citypack_id": outer.citypack_id,
        "outer_citypack_path": str(outer_path.relative_to(root)),
        "outer_citypack_sha256": sha256_file(outer_path),
        "inner_bbox": inner_bbox,
        "outer_bbox": OUTER_BBOX,
        "netconvert_version": version,
        "outer_network_counts": {
            "nodes": len(outer.nodes),
            "directed_edges": len(outer.edges),
            "turns": len(outer.connections or ()),
            "candidate_facilities": len(outer.facilities),
        },
        "network_comparability": _network_diagnostics(inner, outer),
        "method": "Same frozen OSM bytes, conversion flags and version, candidate facility and entrance IDs, origin ID, restriction edge IDs, class, analysis time and fixed-weight routing policy. Rebuilding a larger crop can alter topology, edge lengths and travel times; graph-comparability counts are reported. Full result paths remain in ignored local citypack/runtime.",
        "cases": [_case_summary(root, inner, outer, kind) for kind in CASES],
        "duration_s": round(time.monotonic() - started, 3),
        "reproduce_command": "PYTHONPATH=core:. uv run --frozen python scripts/boundary_sensitivity.py",
        "script_sha256": sha256_file(Path(__file__)),
    }
    destination = output or root / "evidence/wp2/helsinki_boundary_sensitivity.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = run(output=arguments.output)
    print(json.dumps({"status": result["status"], "cases": [
        {key: case[key] for key in ("kind", "fixed_od_count", "difference_count", "comparison_status")}
        for case in result["cases"]
    ]}, indent=2))
