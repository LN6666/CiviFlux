"""Audit whether frozen Berlin prediction edges have observable VIZ counterparts.

The same archived traffic snapshot is supplied as both sides of a no-change
control. Its verdicts are not event validation or prediction accuracy.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "core"), str(ROOT)]

from urbanimpact.citypack.fetch import sha256_file

from scripts.berlin_validation_map import (
    PROBE,
    RAW,
    _receipt_feed_time,
    build,
    compare_snapshots,
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
    traffic = json.loads((ROOT / receipt["traffic"]["local_path"]).read_text())["features"]
    observed, metrics = compare_snapshots(
        bundle["layers"]["predicted_route_impact"]["features"], traffic, traffic
    )
    if metrics["hit"] or metrics["miss"]:
        raise ValueError("same-snapshot negative control reported a traffic change")
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
        "claim_ceiling": "Measurement coverage and no-change pipeline control only. Unmatched prediction edges have unknown real outcomes; no event-hour observations, road-level hit rate, or traffic attribution are present.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
