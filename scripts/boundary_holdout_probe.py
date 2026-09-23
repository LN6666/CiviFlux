#!/usr/bin/env python3
"""Probe the frozen Helsinki outer/further crops from preselected, held-out origins.

These are computational road-node probes, not observed trips or verified facility
entrances. They test whether the selected-case boundary finding generalizes to a
small, spatially spread set of other origins on the same current OSM snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from urbanimpact.contracts import CityPack, Node, Scenario
from urbanimpact.network import Router
from urbanimpact.util import digest, file_hash

from scripts.formal_boundary_case import fixed_targets

ROOT = Path(__file__).resolve().parents[1]
RINGS = ("outer", "further")
KINDS = ("road", "fire")
SELECTION_SALT = "g205-heldout-origins-v1"
ORIGINS_PER_QUADRANT = 2
THRESHOLD_S = 1.0  # Existing case boundary threshold, retained before inspecting probes.


def select_origins(
    outer: CityPack,
    further: CityPack,
    inner_bbox: list[float],
    excluded_node_ids: set[str],
) -> list[dict]:
    """Select two shared passenger junctions per quadrant without route outcomes."""
    if len(inner_bbox) != 4 or not inner_bbox[0] < inner_bbox[2] or not inner_bbox[1] < inner_bbox[3]:
        raise ValueError("Invalid inner boundary")
    eligible_by_crop = []
    for crop in (outer, further):
        entering = {e.target for e in crop.edges if "passenger" in e.allowed_vehicle_classes}
        leaving = {e.source for e in crop.edges if "passenger" in e.allowed_vehicle_classes}
        eligible_by_crop.append(entering & leaving)
    common = eligible_by_crop[0] & eligible_by_crop[1]
    further_nodes = {n.id: n for n in further.nodes}
    mid_lon = (inner_bbox[0] + inner_bbox[2]) / 2
    mid_lat = (inner_bbox[1] + inner_bbox[3]) / 2
    quadrants: dict[str, list[Node]] = {name: [] for name in ("SW", "SE", "NW", "NE")}
    for node in outer.nodes:
        if node.id not in common or node.id in excluded_node_ids:
            continue
        if not (inner_bbox[0] <= node.lon <= inner_bbox[2] and inner_bbox[1] <= node.lat <= inner_bbox[3]):
            continue
        counterpart = further_nodes.get(node.id)
        if counterpart is None or abs(node.lon - counterpart.lon) > 1e-9 or abs(node.lat - counterpart.lat) > 1e-9:
            continue
        quadrant = ("N" if node.lat >= mid_lat else "S") + ("E" if node.lon >= mid_lon else "W")
        quadrants[quadrant].append(node)
    selected = []
    for quadrant in ("SW", "SE", "NW", "NE"):
        ranked = sorted(
            quadrants[quadrant],
            key=lambda n: (hashlib.sha256(f"{SELECTION_SALT}:{n.id}".encode()).hexdigest(), n.id),
        )
        if len(ranked) < ORIGINS_PER_QUADRANT:
            raise ValueError(f"Not enough shared passenger junctions in {quadrant}")
        selected.extend(
            {"node_id": n.id, "lon": n.lon, "lat": n.lat, "quadrant": quadrant}
            for n in ranked[:ORIGINS_PER_QUADRANT]
        )
    return selected


def compare_od(outer_od: list[dict], further_od: list[dict]) -> dict:
    """Report every status/time mismatch; unavailable metrics must remain null."""
    earlier = {(row["origin"], row["facility_id"]): row for row in outer_od}
    later = {(row["origin"], row["facility_id"]): row for row in further_od}
    if len(earlier) != len(outer_od) or len(later) != len(further_od) or earlier.keys() != later.keys():
        raise ValueError("Held-out OD universe changed or contains duplicates")
    differences = []
    paths_changed = comparable_available = stage_count = 0
    max_abs_time_change = 0.0
    status_by_ring = {ring: {stage: Counter() for stage in ("baseline", "event")} for ring in RINGS}
    for key in sorted(earlier):
        before, after = earlier[key], later[key]
        if before["target"] != after["target"]:
            raise ValueError("Held-out OD target node changed across crops")
        for stage in ("baseline", "event"):
            stage_count += 1
            left, right = before[stage], after[stage]
            for ring, route in (("outer", left), ("further", right)):
                status_by_ring[ring][stage][route["status"]] += 1
                if route["status"] != "available" and (
                    route["travel_time_s"] is not None or route["distance_m"] is not None
                ):
                    raise ValueError("Missing route metric was imputed with a number")
            reason = None
            if left["status"] != right["status"]:
                reason = "status_changed"
            elif left["status"] == "available":
                comparable_available += 1
                paths_changed += left["edge_ids"] != right["edge_ids"]
                gap = abs(left["travel_time_s"] - right["travel_time_s"])
                max_abs_time_change = max(max_abs_time_change, gap)
                if gap > THRESHOLD_S:
                    reason = "travel_time_changed_gt_1s"
            if reason:
                differences.append(
                    {
                        "origin": key[0],
                        "facility_id": key[1],
                        "stage": stage,
                        "reason": reason,
                        "outer_status": left["status"],
                        "further_status": right["status"],
                        "outer_travel_time_s": left["travel_time_s"],
                        "further_travel_time_s": right["travel_time_s"],
                        "path_changed_when_both_available":
                            left["edge_ids"] != right["edge_ids"]
                            if left["status"] == right["status"] == "available"
                            else None,
                    }
                )
    return {
        "od_count": len(earlier),
        "stage_comparisons": stage_count,
        "threshold_seconds": THRESHOLD_S,
        "status_counts": {
            ring: {stage: dict(sorted(counts.items())) for stage, counts in stages.items()}
            for ring, stages in status_by_ring.items()
        },
        "comparable_available_stage_count": comparable_available,
        "path_changed_when_both_available_count": paths_changed,
        "max_abs_travel_time_change_s_when_both_available": max_abs_time_change,
        "difference_count": len(differences),
        "differences": differences,
        "observed_metric_stability": not differences,
        "missing_metrics_remain_null": True,
    }


def run(root: Path = ROOT, output: Path | None = None) -> dict:
    boundary_path = root / "evidence/wp2/helsinki_boundary_sensitivity.json"
    formal_path = root / "evidence/wp2/helsinki_formal_boundary_case.json"
    boundary = json.loads(boundary_path.read_text())
    formal = json.loads(formal_path.read_text())
    if boundary["source_sha256"] != formal["source_sha256"]:
        raise ValueError("Frozen source identity differs across boundary reports")
    inner_path = root / "data/citypacks/helsinki-current/citypack.json"
    if file_hash(inner_path) != boundary["inner_citypack_sha256"]:
        raise ValueError("Inner CityPack changed")
    inner = CityPack.model_validate_json(inner_path.read_bytes())
    crops = {}
    for ring in RINGS:
        path = root / f"data/citypacks/helsinki-boundary-{ring}/citypack.json"
        if file_hash(path) != boundary[f"{ring}_citypack_sha256"]:
            raise ValueError(f"{ring} CityPack changed")
        crops[ring] = CityPack.model_validate_json(path.read_bytes())
    targets, excluded = fixed_targets(inner, crops)
    target_hash = digest([(facility.id, facility.entrance_node_id) for facility in targets])
    if target_hash != formal["fixed_candidate_target_hash"] or excluded != formal["excluded_candidate_targets"]:
        raise ValueError("Frozen target cohort differs from formal boundary case")
    heldout = select_origins(
        crops["outer"],
        crops["further"],
        boundary["inner_bbox"],
        {case["origin"] for case in boundary["cases"]}
        | {facility.entrance_node_id for facility in inner.facilities if facility.entrance_node_id},
    )
    origins = [row["node_id"] for row in heldout]
    report = {
        "status": "HELDOUT_PROBE_EXECUTED",
        "claim_boundary": "Current OSM fixed-weight passenger routing from eight deterministic road-junction probes to the 48 original shared candidate entrance nodes. This is not independent observed OD demand, verified facility access, citywide convergence or historical validation.",
        "selection_method": "Before routing, take two shared, coordinate-identical passenger junctions with incoming and outgoing edges per quadrant of the original inner bbox; exclude original case origins and every original candidate entrance; order candidates by SHA256(salt + ':' + node_id). No outcome-based filtering.",
        "selection_salt": SELECTION_SALT,
        "origins_per_quadrant": ORIGINS_PER_QUADRANT,
        "heldout_origins": heldout,
        "inner_bbox": boundary["inner_bbox"],
        "source_sha256": boundary["source_sha256"],
        "source_license": boundary["source_license"],
        "crop_citypack_sha256": {ring: boundary[f"{ring}_citypack_sha256"] for ring in RINGS},
        "fixed_candidate_target_count": len(targets),
        "fixed_candidate_target_hash": target_hash,
        "excluded_candidate_targets": excluded,
        "boundary_report_sha256": file_hash(boundary_path),
        "formal_case_report_sha256": file_hash(formal_path),
        "cases": {},
        "reproduce_command": "PYTHONPATH=core:. .venv/bin/python scripts/boundary_holdout_probe.py",
        "limitations": [
            "The probes reuse the frozen OSM snapshot and unverified candidate entrance nodes; they are held out only from the original origin-based boundary selection.",
            "Eight junctions cannot establish citywide or historical convergence and do not replace human/source review of three excluded and two resnapped entrances.",
            "Road/fire restrictions, class and analysis time are the two declared what-if scenarios, not measured event ground truth.",
        ],
    }
    scoped = {ring: crop.model_copy(update={"facilities": targets}) for ring, crop in crops.items()}
    for kind in KINDS:
        scenario_path = root / f"evidence/wp1/{kind}_scenario.json"
        if file_hash(scenario_path) != formal["cases"][kind]["original_scenario_file_sha256"]:
            raise ValueError(f"Frozen {kind} scenario changed")
        scenario = Scenario.model_validate_json(scenario_path.read_bytes())
        outcomes = {}
        for ring in RINGS:
            adapted = scenario.model_copy(update={"citypack_id": scoped[ring].citypack_id})
            outcomes[ring] = Router().compare(scoped[ring], adapted, origins=origins)["od"]
        report["cases"][kind] = compare_od(outcomes["outer"], outcomes["further"])
        report["cases"][kind]["scenario_file_sha256"] = file_hash(scenario_path)
    report["script_sha256"] = file_hash(Path(__file__))
    destination = output or root / "evidence/wp2/helsinki_boundary_holdout_probe.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(output=args.output)
    print(json.dumps({kind: {"od_count": case["od_count"], "difference_count": case["difference_count"]} for kind, case in result["cases"].items()}, indent=2))
