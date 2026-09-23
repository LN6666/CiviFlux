#!/usr/bin/env python3
"""Rebuild nested Helsinki road graphs and compare the same candidate ODs.

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
from urbanimpact.network import Router, compare_boundaries

from adapters.osm import convert_network, extract_roi

ROOT = Path(__file__).resolve().parents[1]
OUTER_BBOX = [24.9, 60.15, 25.025, 60.215]
FURTHER_BBOX = [24.875, 60.135, 25.05, 60.23]
RINGS = (("outer", OUTER_BBOX), ("further", FURTHER_BBOX))
CASES = ("road", "fire")


def _contains(inner_bbox: list[float], outer_bbox: list[float]) -> bool:
    return (
        outer_bbox[0] <= inner_bbox[0] < inner_bbox[2] <= outer_bbox[2]
        and outer_bbox[1] <= inner_bbox[1] < inner_bbox[3] <= outer_bbox[3]
    )


def _fixed_facilities(inner: CityPack, enlarged: list[tuple[str, CityPack]]) -> tuple[tuple, list[dict]]:
    """Freeze source facility and entrance identity across every crop."""
    enlarged_nodes = [(name, {node.id for node in crop.nodes}) for name, crop in enlarged]
    enlarged_facilities = [(name, {facility.id for facility in crop.facilities}) for name, crop in enlarged]
    selected = []
    excluded = []
    for facility in inner.facilities:
        reason = None
        if facility.entrance_node_id is None:
            reason = "candidate entrance unknown in inner crop"
        else:
            missing_facility = [name for name, ids in enlarged_facilities if facility.id not in ids]
            missing_entrance = [name for name, ids in enlarged_nodes if facility.entrance_node_id not in ids]
            if missing_facility:
                reason = f"facility absent in {','.join(missing_facility)} extraction"
            elif missing_entrance:
                reason = f"inner candidate entrance node absent in {','.join(missing_entrance)} graph"
        if reason:
            excluded.append({"facility_id": facility.id, "reason": reason})
        else:
            selected.append(facility)
    if not selected:
        raise ValueError("No fixed facility entrances are shared across all crops")
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
        "shared_edges_with_changed_permissions": sum(
            inner_edges[edge_id].allowed_vehicle_classes != outer_edges[edge_id].allowed_vehicle_classes
            for edge_id in shared_ids
        ),
        "shared_turns": len(shared_turns),
        "inner_turns_absent_outer": len(inner_turns.keys() - outer_turns.keys()),
        "outer_turns_absent_inner": len(outer_turns.keys() - inner_turns.keys()),
        "shared_turns_with_changed_permissions": sum(
            inner_turns[turn_id].allowed_vehicle_classes != outer_turns[turn_id].allowed_vehicle_classes
            for turn_id in shared_turns
        ),
    }


def _route_diagnostics(earlier: CityPack, later: CityPack, scenario: Scenario, origin: str) -> dict:
    """Distinguish threshold agreement from exact paths and travel weights."""
    outcomes = []
    for crop in (earlier, later):
        scoped = scenario.model_copy(update={"citypack_id": crop.citypack_id})
        outcomes.append(Router().compare(crop, scoped, origins=[origin])["od"])
    if len(outcomes[0]) != len(outcomes[1]):
        raise ValueError("OD counts changed across crops")
    stage_count = status_changes = changed_paths = comparable_available = 0
    max_time_change = 0.0
    for before, after in zip(*outcomes):
        if (before["origin"], before["facility_id"]) != (after["origin"], after["facility_id"]):
            raise ValueError("OD identities changed across crops")
        for stage in ("baseline", "event"):
            stage_count += 1
            earlier_route, later_route = before[stage], after[stage]
            if earlier_route["status"] != later_route["status"]:
                status_changes += 1
            if earlier_route["status"] == later_route["status"] == "available":
                comparable_available += 1
                changed_paths += earlier_route["edge_ids"] != later_route["edge_ids"]
                max_time_change = max(
                    max_time_change,
                    abs(earlier_route["travel_time_s"] - later_route["travel_time_s"]),
                )
    return {
        "stage_comparisons": stage_count,
        "status_changed_stage_count": status_changes,
        "available_in_both_stage_count": comparable_available,
        "path_changed_when_both_available_stage_count": changed_paths,
        "max_abs_travel_time_change_s_when_both_available": max_time_change,
    }


def _case_summary(root: Path, crops: list[tuple[str, CityPack]], kind: str) -> dict:
    inner = crops[0][1]
    scenario = Scenario.model_validate_json((root / f"evidence/wp1/{kind}_scenario.json").read_bytes())
    if scenario.citypack_id != inner.citypack_id:
        raise ValueError(f"{kind} scenario does not match frozen inner citypack")
    inner_edges = {edge.id: edge for edge in inner.edges}
    restrictions = {edge_id for restriction in scenario.restrictions for edge_id in restriction.edge_ids}
    seed = scenario.seed_spec.entity_ids[0]
    if seed not in inner_edges:
        raise ValueError(f"{kind} origin seed is absent from inner graph")
    origin = inner_edges[seed].source
    for name, crop in crops[1:]:
        edge_ids = {edge.id for edge in crop.edges}
        if not restrictions <= edge_ids:
            raise ValueError(f"{kind} restrictions are absent from {name} graph")
        if seed not in edge_ids or origin not in {node.id for node in crop.nodes}:
            raise ValueError(f"{kind} origin seed or fixed origin node is absent from {name} graph")

    fixed, excluded = _fixed_facilities(inner, crops[1:])
    paired_crops = [(name, crop.model_copy(update={"facilities": fixed})) for name, crop in crops]
    pairwise = []
    for (earlier_name, earlier), (later_name, later) in zip(paired_crops, paired_crops[1:]):
        comparison = compare_boundaries(earlier, later, scenario, [origin], threshold_seconds=1.0)
        diffs = []
        for difference in comparison["differences"]:
            before, after = difference.get("inner"), difference.get("outer")
            diffs.append(
                {
                    "facility_id": difference["facility_id"],
                    "stage": difference.get("stage"),
                    "reason": difference.get("reason", "status or time differs beyond threshold"),
                    "earlier_status": before["status"] if before else None,
                    "later_status": after["status"] if after else None,
                    "earlier_travel_time_s": before["travel_time_s"] if before else None,
                    "later_travel_time_s": after["travel_time_s"] if after else None,
                    "route_edge_ids_changed": before["edge_ids"] != after["edge_ids"]
                    if before and after
                    else None,
                }
            )
        pairwise.append(
            {
                "earlier_crop": earlier_name,
                "later_crop": later_name,
                "comparison_status": comparison["status"],
                "threshold_seconds": comparison["threshold_seconds"],
                "difference_count": len(diffs),
                "differences_by_stage": dict(Counter(d.get("stage") or "unpaired" for d in diffs)),
                "differences": diffs,
                "earlier_network_hash": comparison["inner_network_hash"],
                "later_network_hash": comparison["outer_network_hash"],
            }
        )
    first, last = pairwise[0], pairwise[-1]
    return {
        "kind": kind,
        "origin": origin,
        "origin_seed_edge": seed,
        "vehicle_class": "passenger",
        "restricted_edge_count": len(restrictions),
        "restricted_edges_shared": True,
        "fixed_od_count": len(fixed),
        "excluded_candidate_targets": excluded,
        "origin_seed_source_by_crop": {
            name: next(edge.source for edge in crop.edges if edge.id == seed) for name, crop in crops
        },
        "comparison_status": first["comparison_status"],
        "threshold_seconds": first["threshold_seconds"],
        "difference_count": first["difference_count"],
        "differences_by_stage": first["differences_by_stage"],
        "differences": first["differences"],
        "inner_network_hash": first["earlier_network_hash"],
        "outer_network_hash": first["later_network_hash"],
        "ring_comparisons": pairwise,
        "observed_last_pair_metric_stability": last["comparison_status"] == "stable",
        "last_pair_route_diagnostics": _route_diagnostics(
            paired_crops[-2][1], paired_crops[-1][1], scenario, origin
        ),
        "stability_interpretation": "Only the same fixed OD metric/status at a 1 s threshold across the last two crops. Route identity is measured separately; citywide and historical convergence are not certified.",
    }


def _build_crop(
    root: Path,
    inner: CityPack,
    source_hash: str,
    netconvert: Path,
    version: str,
    name: str,
    bbox: list[float],
) -> tuple[CityPack, Path]:
    target_dir = root / f"data/citypacks/helsinki-boundary-{name}"
    target_dir.mkdir(parents=True, exist_ok=True)
    extraction = extract_roi(root / "data/raw/hsl.osm.pbf", target_dir / "outer.osm.xml", bbox)
    network = convert_network(
        target_dir / "outer.osm.xml",
        target_dir / "outer.net.xml",
        netconvert,
        target_dir / "netconvert.log",
        extraction,
    )
    if inner.evidence["network_converter"]["command"][5:] != network["conversion"]["command"][5:]:
        raise ValueError(f"Network conversion flags differ in {name} crop")
    data = inner.model_dump(mode="json")
    data.update({key: network[key] for key in ("nodes", "edges", "connections", "facilities")})
    data["citypack_id"] = (
        f"helsinki-boundary-{name}-"
        + hashlib.sha256(
            json.dumps([source_hash, bbox, version], separators=(",", ":")).encode()
        ).hexdigest()[:12]
    )
    data["evidence"] = {
        **inner.evidence,
        "bbox": bbox,
        "scope": "enlarged current road network for fixed-OD boundary sensitivity only",
        "network_converter": network["conversion"],
        "osm_restriction_relations": extraction["restriction_relations"],
        "conditional_access_way_ids": extraction["conditional_tag_way_ids"],
        "sumo_network_path": str((target_dir / "outer.net.xml").relative_to(root)),
        "boundary_stability": "SCENARIO_SPECIFIC_COMPARISON_RECORDED_SEPARATELY",
    }
    data["warnings"] = [
        *inner.warnings,
        "GTFS and facility identity are frozen from the inner snapshot for road-boundary comparison.",
    ]
    crop = CityPack.model_validate(data)
    path = target_dir / "citypack.json"
    path.write_text(crop.model_dump_json() + "\n")
    return crop, path


def run(root: Path = ROOT, output: Path | None = None) -> dict:
    started = time.monotonic()
    inner_path = root / "data/citypacks/helsinki-current/citypack.json"
    raw_path = root / "data/raw/hsl.osm.pbf"
    inner = CityPack.model_validate_json(inner_path.read_bytes())
    inner_bbox = inner.evidence["bbox"]
    bounds = [inner_bbox, *(bbox for _, bbox in RINGS)]
    for earlier, later in zip(bounds, bounds[1:]):
        if not _contains(earlier, later):
            raise ValueError("Boundary sensitivity crops must be strictly nested")
    osm_source = next(source for source in inner.sources if source.id == "S03-OSM")
    if sha256_file(raw_path) != osm_source.sha256:
        raise ValueError("Frozen OSM source hash differs from the inner citypack")
    netconvert = root / ".venv/bin/netconvert"
    version = subprocess.check_output([str(netconvert), "--version"], text=True).splitlines()[0]
    if version != "Eclipse SUMO netconvert 1.27.1":
        raise ValueError(f"Unexpected netconvert version: {version}")

    crops = [("inner", inner)]
    crop_paths = {}
    for name, bbox in RINGS:
        crop, path = _build_crop(root, inner, osm_source.sha256, netconvert, version, name, bbox)
        crops.append((name, crop))
        crop_paths[name] = path
    outer = crops[1][1]
    final = crops[-1][1]
    cases = [_case_summary(root, crops, kind) for kind in CASES]
    last_pair_stable = all(case["observed_last_pair_metric_stability"] for case in cases)

    report = {
        "status": "PASS_SCOPE_MULTI_RING_BOUNDARY_CHECK_EXECUTED",
        "claim_boundary": "Current OSM fixed-weight routing at selected origins and candidate entrances only; adjacent-ring agreement is limited evidence and never proves historical, citywide or global convergence.",
        "observed_final_pair_metric_status": "stable" if last_pair_stable else "not_stable",
        "source_sha256": osm_source.sha256,
        "source_license": "ODbL-1.0, © OpenStreetMap contributors; imported via HSL",
        "inner_citypack_id": inner.citypack_id,
        "inner_citypack_sha256": sha256_file(inner_path),
        "outer_citypack_id": outer.citypack_id,
        "outer_citypack_path": str(crop_paths["outer"].relative_to(root)),
        "outer_citypack_sha256": sha256_file(crop_paths["outer"]),
        "further_citypack_id": final.citypack_id,
        "further_citypack_path": str(crop_paths["further"].relative_to(root)),
        "further_citypack_sha256": sha256_file(crop_paths["further"]),
        "inner_bbox": inner_bbox,
        "outer_bbox": OUTER_BBOX,
        "further_bbox": FURTHER_BBOX,
        "netconvert_version": version,
        "outer_network_counts": {
            "nodes": len(outer.nodes),
            "directed_edges": len(outer.edges),
            "turns": len(outer.connections or ()),
            "candidate_facilities": len(outer.facilities),
        },
        "further_network_counts": {
            "nodes": len(final.nodes),
            "directed_edges": len(final.edges),
            "turns": len(final.connections or ()),
            "candidate_facilities": len(final.facilities),
        },
        "network_comparability": _network_diagnostics(inner, outer),
        "network_comparability_by_pair": [
            {"earlier_crop": earlier_name, "later_crop": later_name, **_network_diagnostics(earlier, later)}
            for (earlier_name, earlier), (later_name, later) in zip(crops, crops[1:])
        ],
        "method": "Nested crops from the same frozen OSM bytes, netconvert flags and version; one fixed origin and candidate facility/entrance intersection across all crops, identical restriction IDs, class, analysis time, and routing policy. Each adjacent crop pair is checked at 1 s. Independent conversions can alter edge IDs, endpoints, lengths, travel weights and turn topology, so agreement is only observed metric stability for these ODs. Full graphs remain ignored local runtime data.",
        "cases": cases,
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
    print(
        json.dumps(
            {
                "status": result["status"],
                "cases": [
                    {
                        key: case[key]
                        for key in ("kind", "fixed_od_count", "difference_count", "comparison_status")
                    }
                    for case in result["cases"]
                ],
            },
            indent=2,
        )
    )
