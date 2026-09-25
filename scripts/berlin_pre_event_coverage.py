"""Audit whether frozen Berlin prediction edges have observable VIZ counterparts.

The same archived traffic snapshot is supplied as both sides of a no-change
control. Its verdicts are not event validation or prediction accuracy.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "core"), str(ROOT)]

from urbanimpact.citypack.fetch import sha256_file

from scripts.berlin_validation_map import (
    PROBE,
    RAW,
    _metric_line,
    _receipt_feed_time,
    build,
    compare_snapshots,
    summarize_control_indicator,
)

SNAPSHOT = "sep25-pre-event-evening"
OUTPUT = ROOT / "evidence/events/berlin-2026-viz-pre-event-coverage.json"


def main() -> None:
    receipt_path = RAW / f"{SNAPSHOT}-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    feed_time, feed_age_s = _receipt_feed_time(receipt, "pre-event coverage")
    probe = json.loads(PROBE.read_text())
    if feed_time <= datetime.fromisoformat(probe["frozen_at_utc"]):
        raise ValueError("coverage snapshot must follow frozen prediction")
    runtime_bundle = ROOT / ".runtime/berlin-pre-event-coverage-bundle.json"
    build(SNAPSHOT, output=runtime_bundle)
    bundle = json.loads(runtime_bundle.read_text())
    control_plan = bundle["control_plan"]
    traffic = json.loads((ROOT / receipt["traffic"]["local_path"]).read_text())["features"]
    observed, metrics = compare_snapshots(
        bundle["layers"]["predicted_route_impact"]["features"], traffic, traffic
    )
    if metrics["hit"] or metrics["miss"]:
        raise ValueError("same-snapshot negative control reported a traffic change")
    control_indicator = summarize_control_indicator(control_plan, observed)
    if control_indicator["median_pair_adjusted_speed_drop_fraction"] != 0:
        raise ValueError("same-snapshot matched controls reported a speed change")
    excluded = unary_union([
        _metric_line(feature["geometry"]["coordinates"])
        for layer in ("predicted_route_impact", "restriction_inputs")
        for feature in bundle["layers"][layer]["features"]
    ])
    control_distances = [
        _metric_line(feature["geometry"]["coordinates"]).distance(excluded)
        for feature in bundle["layers"]["viz_controls"]["features"]
    ]
    if control_distances and min(control_distances) < 200:
        raise ValueError("selected control overlaps the 200 m exclusion zone")
    report = {
        "schema_version": "1.0",
        "status": "PRE_EVENT_COVERAGE_ONLY_NOT_EVENT_VALIDATION",
        "case_id": "berlin-marathon-2026",
        "prediction_frozen_at_utc": probe["frozen_at_utc"],
        "prediction_sha256": sha256_file(PROBE),
        "snapshot_feed_utc": feed_time.isoformat(),
        "snapshot_feed_age_at_capture_s": feed_age_s,
        "snapshot_receipt_sha256": sha256_file(receipt_path),
        "snapshot_traffic_sha256": receipt["traffic"]["sha256"],
        "method": "Same archived pre-event VIZ snapshot on both sides of compare_snapshots; fixed 1 km evaluation corridor and 18 m directional geometry matching.",
        "frozen_predicted_directed_edges": metrics["predicted_edge_count"],
        "predicted_edges_with_viz_match": metrics["predicted_edges_with_viz_match"],
        "predicted_edges_without_viz_match": metrics["predicted_edges_without_viz_match"],
        "matched_viz_directed_segments": metrics["matched_viz_segments"],
        "scored_matched_viz_directed_segments": metrics["scored_matched_viz_segments"],
        "viz_segments_in_evaluation_area": len(observed),
        "scorable_viz_segments_in_evaluation_area": metrics["scored_segments"],
        "preexisting_closed_or_other_unscored_viz_segments": metrics["unscored"],
        "no_change_control_hits": metrics["hit"],
        "no_change_control_misses": metrics["miss"],
        "baseline_only_control_method": control_plan["method"],
        "control_treated_viz_segments": control_plan["treated_segments"],
        "control_treated_segments_with_match": control_plan["treated_segments_with_controls"],
        "selected_control_viz_segments": control_plan["control_segments"],
        "minimum_control_exclusion_distance_m": round(min(control_distances), 1) if control_distances else None,
        "control_selection_sha256": control_plan["selection_sha256"],
        "no_change_control_valid_groups": control_indicator["valid_treated_control_groups"],
        "no_change_control_adjusted_speed_drop_fraction": control_indicator["median_pair_adjusted_speed_drop_fraction"],
        "claim_ceiling": "Measurement coverage and baseline-only control-selection feasibility, with no-change pipeline control. Selected controls can be affected by spillover and do not establish an event counterfactual. Unmatched prediction edges have unknown real outcomes; no event-hour observations, road-level hit rate, or traffic attribution are present.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
