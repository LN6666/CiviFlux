"""Replay the fixed Helsinki road/fire cases on two enlarged offline networks.

The outer crop is the proposed *case* boundary and the further crop is its
independent sensitivity check. This does not validate historical traffic,
facility entrances, citywide coverage, or emergency response times.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from pathlib import Path

from urbanimpact.contracts import ActionRequest, CityPack, Facility, Scenario
from urbanimpact.util import atomic_json, digest, file_hash

from api.services import RunService

ROOT = Path(__file__).resolve().parents[1]
CROPS = {
    "outer": "data/citypacks/helsinki-boundary-outer/citypack.json",
    "further": "data/citypacks/helsinki-boundary-further/citypack.json",
}
KINDS = ("road", "fire")
THRESHOLD_S = 1.0


def fixed_targets(inner: CityPack, crops: dict[str, CityPack]) -> tuple[tuple[Facility, ...], list[dict]]:
    """Keep exactly the original candidate entrance identities shared by both rings."""
    nodes = {name: {n.id for n in crop.nodes} for name, crop in crops.items()}
    facilities = {name: {f.id for f in crop.facilities} for name, crop in crops.items()}
    kept = []
    excluded = []
    for facility in inner.facilities:
        absent = [name for name in crops if facility.id not in facilities[name]]
        missing_node = [name for name in crops if facility.entrance_node_id not in nodes[name]]
        if facility.entrance_node_id is None:
            reason = "candidate entrance unknown in inner crop"
        elif absent:
            reason = f"facility absent in {','.join(absent)} extraction"
        elif missing_node:
            reason = f"inner candidate entrance node absent in {','.join(missing_node)} graph"
        else:
            kept.append(facility)
            continue
        excluded.append({"facility_id": facility.id, "reason": reason})
    if not kept:
        raise ValueError("No shared fixed candidate entrances")
    return tuple(kept), excluded


def scoped_city(crop: CityPack, targets: tuple[Facility, ...], ring: str) -> CityPack:
    target_hash = digest([(f.id, f.entrance_node_id) for f in targets])
    proposed = crop.model_copy(
        update={
            "citypack_id": f"{crop.citypack_id}-fixedod-{target_hash[:12]}",
            "facilities": targets,
            "evidence": {
                **crop.evidence,
                "case_boundary_ring": ring,
                "base_citypack_id": crop.citypack_id,
                "fixed_candidate_target_hash": target_hash,
                "target_policy": "original inner candidate entrances shared across both enlarged crops",
            },
            "warnings": crop.warnings
            + ("Only the frozen candidate entrance intersection is evaluated; other facilities are out of scope.",),
        }
    )
    return CityPack.model_validate(proposed.model_dump(mode="python"))


def adapted_scenario(original: Scenario, city: CityPack, ring: str) -> Scenario:
    edge_ids = {e.id for e in city.edges}
    if not all(set(r.edge_ids) <= edge_ids for r in original.restrictions):
        raise ValueError(f"Restriction edges absent from {ring} crop")
    if not set(original.seed_spec.entity_ids) <= edge_ids:
        raise ValueError(f"Seed edge absent from {ring} crop")
    proposed = original.model_copy(
        update={
            "scenario_id": f"{original.scenario_id}-{ring}-fixedod",
            "citypack_id": city.citypack_id,
        }
    )
    scenario = Scenario.model_validate(proposed.model_dump(mode="python"))
    if scenario.restrictions != original.restrictions or scenario.seed_spec != original.seed_spec:
        raise ValueError("Frozen scenario restrictions or seeds changed")
    if (scenario.analysis_at, scenario.window, scenario.analysis_vehicle_class) != (
        original.analysis_at,
        original.window,
        original.analysis_vehicle_class,
    ):
        raise ValueError("Frozen scenario physical context changed")
    return scenario


def od_summary(od: list[dict]) -> dict:
    stage_status = {stage: dict(sorted(Counter(row[stage]["status"] for row in od).items())) for stage in ("baseline", "event")}
    missing_nonzero = [
        (row["facility_id"], stage)
        for row in od
        for stage in ("baseline", "event")
        if row[stage]["status"] != "available"
        and (row[stage]["travel_time_s"] is not None or row[stage]["distance_m"] is not None)
    ]
    if missing_nonzero:
        raise ValueError(f"Missing route metrics were represented as numbers: {missing_nonzero[:3]}")
    deltas = [row["delta_travel_time_s"] for row in od if row["delta_travel_time_s"] is not None]
    return {
        "od_count": len(od),
        "stage_status": stage_status,
        "missing_metrics_are_null": True,
        "paired_available_count": len(deltas),
        "positive_delta_count": sum(value > 1e-9 for value in deltas),
        "negative_delta_count": sum(value < -1e-9 for value in deltas),
        "max_positive_delta_travel_time_s": max((value for value in deltas if value > 0), default=None),
    }


def execute_product(city: CityPack, scenario: Scenario, runtime_root: Path) -> tuple[dict, list[dict]]:
    """Use the typed Action -> RunService -> routing/KG/PPR product path."""
    service = RunService(runtime_root, [city])
    try:
        service.action(
            ActionRequest(
                action_id="create-fixed-boundary-case",
                action_type="CreateScenario",
                scenario_id=scenario.scenario_id,
                parameters={"scenario": scenario.model_dump(mode="json")},
            )
        )
        job = service.submit(city.citypack_id, scenario.scenario_id)
        service.futures[job["run_id"]].result(timeout=600)
        state = service.state(job["run_id"])
        if state["status"] != "completed":
            raise RuntimeError(f"Product run failed: {state['error']}")
        result = service.result(job["run_id"])
        od = result["facts"]["od"]
        expected = {f.id for f in city.facilities}
        if len(od) != len(expected) or {row["facility_id"] for row in od} != expected:
            raise ValueError("Product failed to evaluate every fixed candidate OD")
        if result["attention"].get("convergence") is not True:
            raise ValueError("Product PPR did not converge")
        graph = result["graph"]
        facts_without_cache = {k: v for k, v in result["facts"].items() if k != "physical_cache"}
        summary = {
            "product_run_status": state["status"],
            "product_path": "typed CreateScenario/RunScenario Actions -> RunService -> Router -> ontology projection -> fixed PPR",
            "scoped_citypack_id": city.citypack_id,
            "adapted_scenario_id": scenario.scenario_id,
            "provider_mode": result["provider_mode"],
            "engine": scenario.engine,
            "ranking": scenario.ranking,
            "source_snapshot_hash": result["source_snapshot_hash"],
            "scenario_hash": digest(scenario),
            "restrictions_hash": digest(sorted(e for r in scenario.restrictions for e in r.edge_ids)),
            "origin_seed_hash": digest(scenario.seed_spec.entity_ids),
            "physical_facts_hash_excluding_cache_state": digest(facts_without_cache),
            "projection_hash": result["projection_hash"],
            "graph_nodes": len(graph["event"]["nodes"]),
            "graph_links": {stage: len(graph[stage]["links"]) for stage in ("baseline", "event")},
            "ppr_residual_l1": result["attention"]["residual_l1"],
            "ppr_delta_sum": result["attention"]["delta_sum"],
            "od_summary": od_summary(od),
        }
        if summary["provider_mode"] != "rules" or summary["engine"] != "routing" or summary["ranking"] != "A2":
            raise ValueError("Unexpected live provider or physical engine in offline case")
        return summary, od
    finally:
        service.close()


def compare_products(outer: list[dict], further: list[dict]) -> dict:
    earlier = {row["facility_id"]: row for row in outer}
    later = {row["facility_id"]: row for row in further}
    if earlier.keys() != later.keys():
        raise ValueError("Candidate target universe changed")
    changes = []
    stages = 0
    changed_paths = 0
    max_time_change = 0.0
    for facility_id in sorted(earlier):
        before, after = earlier[facility_id], later[facility_id]
        if (before["origin"], before["target"]) != (after["origin"], after["target"]):
            raise ValueError("Fixed origin/target identity changed")
        for stage in ("baseline", "event"):
            stages += 1
            left, right = before[stage], after[stage]
            if left["status"] != right["status"]:
                changes.append({"facility_id": facility_id, "stage": stage, "reason": "status_change"})
            elif left["status"] == "available":
                change = abs(left["travel_time_s"] - right["travel_time_s"])
                max_time_change = max(max_time_change, change)
                changed_paths += left["edge_ids"] != right["edge_ids"]
                if change > THRESHOLD_S:
                    changes.append({"facility_id": facility_id, "stage": stage, "reason": "time_change_gt_1s", "difference_s": change})
    return {
        "stage_comparisons": stages,
        "threshold_seconds": THRESHOLD_S,
        "status_or_time_changes_exceeding_threshold": changes,
        "path_changed_when_both_available_count": changed_paths,
        "max_abs_travel_time_change_s_when_both_available": max_time_change,
        "observed_fixed_od_metric_stability": not changes,
    }


def run(root: Path = ROOT, output: Path | None = None) -> dict:
    boundary = json.loads((root / "evidence/wp2/helsinki_boundary_sensitivity.json").read_text())
    if boundary["observed_final_pair_metric_status"] != "stable":
        raise ValueError("Outer/further comparison is not stable in the frozen boundary evidence")
    inner_path = root / "data/citypacks/helsinki-current/citypack.json"
    if file_hash(inner_path) != boundary["inner_citypack_sha256"]:
        raise ValueError("Frozen inner CityPack hash changed")
    inner = CityPack.model_validate_json(inner_path.read_bytes())
    crops = {}
    for ring, relative_path in CROPS.items():
        path = root / relative_path
        if file_hash(path) != boundary[f"{ring}_citypack_sha256"]:
            raise ValueError(f"Frozen {ring} CityPack hash changed")
        crops[ring] = CityPack.model_validate_json(path.read_bytes())
    targets, excluded = fixed_targets(inner, crops)
    if len(targets) != 48 or len(excluded) != 3:
        raise ValueError("Frozen fixed-OD coverage unexpectedly changed")
    if any(case["excluded_candidate_targets"] != excluded for case in boundary["cases"]):
        raise ValueError("Excluded candidate targets differ from boundary evidence")

    report = {
        "status": "PASS_SCOPED_CURRENT_NETWORK_CASE_REPLAY",
        "formal_case_boundary": "outer",
        "boundary_sensitivity_check_ring": "further",
        "selection_criterion": "Keep the smallest enlarged ring for which the next independently converted ring preserves all 48 frozen origin-to-candidate-target baseline/event statuses and paths, with each available travel time differing by at most 1 s; hold source bytes, scenario restrictions, seeds, class and analysis time fixed.",
        "claim_boundary": "Only the two declared Helsinki what-if cases, 48 shared candidate entrances, selected origins, passenger class, fixed edge travel times and current OSM network. Adjacent outer/further agreement is observed at 1 s, not citywide, historical or emergency-response validation.",
        "source_sha256": boundary["source_sha256"],
        "source_license": boundary["source_license"],
        "crop_paths": CROPS,
        "crop_citypack_sha256": {ring: boundary[f"{ring}_citypack_sha256"] for ring in CROPS},
        "crop_bbox_lon_lat": {ring: boundary[f"{ring}_bbox"] for ring in CROPS},
        "outer_further_network_differences": boundary["network_comparability_by_pair"][1],
        "inner_original_candidate_facilities": len(inner.facilities),
        "fixed_candidate_target_count": len(targets),
        "fixed_candidate_target_hash": digest([(f.id, f.entrance_node_id) for f in targets]),
        "fixed_target_policy": "freeze original inner candidate entrance IDs; do not silently resnap or reinterpret them as verified entrances",
        "excluded_candidate_targets": excluded,
        "excluded_target_metric_status": "unknown/not evaluated; no imputed zero, unreachable or available value",
        "candidate_entrance_count_in_native_crops": {ring: len(crop.facilities) for ring, crop in crops.items()},
        "native_entrance_resnap_ids": {
            ring: sorted(
                f.id
                for f in targets
                if next(x for x in crop.facilities if x.id == f.id).entrance_node_id != f.entrance_node_id
            )
            for ring, crop in crops.items()
        },
        "cases": {},
        "reproduce_command": "PYTHONPATH=core:. uv run --frozen python scripts/formal_boundary_case.py",
        "remaining_validation": [
            "Before G205 can claim full original-case coverage, independently map the three excluded original candidate entrances onto the enlarged networks or explicitly approve a narrower 48-target case universe.",
            "Review the two native-crop resnaps and choose a source-backed canonical entrance for each; this replay deliberately holds the inner candidate target nodes fixed.",
            "Candidate facility entrances and announced/assumed incident geometry require human/source review before operational use.",
            "The outer/further pair is not proof of convergence under every larger crop or of measured historical traffic outcomes.",
        ],
        "g205_interpretation": "The enlarged-network and null-metric checks pass for the declared 48-target current-network case. Full original-case entrance coverage and human-reviewed facility mapping remain partial.",
    }
    runtime = root / ".runtime/helsinki_formal_boundary_case"
    runtime.mkdir(parents=True, exist_ok=True)
    for kind in KINDS:
        original_path = root / f"evidence/wp1/{kind}_scenario.json"
        original = Scenario.model_validate_json(original_path.read_bytes())
        if original.citypack_id != inner.citypack_id:
            raise ValueError(f"Frozen {kind} scenario CityPack mismatch")
        cases = {}
        rows = {}
        for ring, crop in crops.items():
            city = scoped_city(crop, targets, ring)
            scenario = adapted_scenario(original, city, ring)
            with tempfile.TemporaryDirectory(prefix=f"{kind}-{ring}-", dir=runtime) as workspace:
                summary, od = execute_product(city, scenario, Path(workspace))
            cases[ring] = summary
            rows[ring] = od
        if cases["outer"]["restrictions_hash"] != cases["further"]["restrictions_hash"]:
            raise ValueError("Restriction IDs changed across crops")
        comparison = compare_products(rows["outer"], rows["further"])
        if not comparison["observed_fixed_od_metric_stability"] or comparison[
            "path_changed_when_both_available_count"
        ]:
            raise ValueError(f"{kind} product metrics or routes differ between outer and further crops")
        report["cases"][kind] = {
            "original_scenario_file_sha256": file_hash(original_path),
            "original_scenario_hash": digest(original),
            "original_scenario_id": original.scenario_id,
            "origin_node_id": next(case["origin"] for case in boundary["cases"] if case["kind"] == kind),
            "origin_seed_edge_id": original.seed_spec.entity_ids[0],
            "analysis_at": original.analysis_at.isoformat(),
            "vehicle_class": original.analysis_vehicle_class,
            "restriction_edge_count": len({e for r in original.restrictions for e in r.edge_ids}),
            "products": cases,
            "outer_vs_further": comparison,
        }
    report["script_sha256"] = file_hash(Path(__file__))
    atomic_json(output or root / "evidence/wp2/helsinki_formal_boundary_case.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(output=args.output)
    print(result["status"], ", ".join(result["cases"]))
