"""Read-only snapshot inventory of named evidence for Helsinki historical claims.

This is not a backtest or score. It deliberately never treats a successful
product run, a current snapshot, or a source announcement as observed impact.
The inventory covers INPUTS only; new evidence sources require explicit review
and registry extension before this report can say anything about them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

INPUTS = (
    "evidence/wp1/citypack_audit.json",
    "evidence/wp1/case_review.json",
    "evidence/wp1/missing_data_report.json",
    "evidence/wp1/evaluation_split_manifest.json",
    "cases/helsinki_cityrun_2026/case_evidence.json",
    "cases/helsinki_fire_2026/case_evidence.json",
)


def _load(root: Path, name: str) -> tuple[dict[str, Any], str]:
    data = (root / name).read_bytes()
    value = json.loads(data)
    if not isinstance(value, dict):
        raise TypeError(f"Expected JSON object: {name}")
    return value, hashlib.sha256(data).hexdigest()


def assess(root: Path) -> dict[str, Any]:
    loaded = {name: _load(root, name) for name in INPUTS}
    audit = loaded[INPUTS[0]][0]
    review = loaded[INPUTS[1]][0]
    missing = loaded[INPUTS[2]][0]
    split = loaded[INPUTS[3]][0]
    road = loaded[INPUTS[4]][0]
    fire = loaded[INPUTS[5]][0]

    road_review = review.get("road_case", {})
    fire_review = review.get("fire_case", {})
    mapped = road_review.get("candidate_mapped_fact_count", 0)
    accepted = road_review.get("human_accepted_mapping_count", 0)
    source_count = road_review.get("motor_road_fact_count", 0)
    coverage = audit.get("gtfs_coverage", {}).get("historical_case_dates", {})
    event_dates = road.get("event_dates", [])
    fire_date = fire.get("event_date")
    historical_gtfs = bool(event_dates and fire_date) and all(
        coverage.get(date) is True for date in [*event_dates, fire_date]
    )
    historical_network = missing.get("historical_network") == "VALIDATED_EVENT_DATE"
    traffic = missing.get("traffic_counts", {})
    measured_targets = split.get("heldout_measured_targets", [])
    actual_road_operation_verified = road_review.get("observed_operation_verified") is True

    return {
        "schema_version": "1.0",
        "purpose": "Evidence-readiness inventory only; no model execution or scientific score",
        "scope": "Snapshot of INPUTS only; new evidence sources require registry extension and review",
        "input_sha256": {name: digest for name, (_, digest) in loaded.items()},
        "citypack": {
            "status": audit.get("status"),
            "id": audit.get("citypack_id"),
            "historical_network_ready": historical_network,
            "gtfs_covers_both_events": historical_gtfs,
        },
        "R1": {
            "source_fact_kind": road.get("source_status"),
            "planned_not_observed": road.get("source_status") == "planned_notice_web_verified",
            "actual_operated_restriction_verified": actual_road_operation_verified,
            "motor_road_fact_count": source_count,
            "candidate_mapped_count": mapped,
            "human_accepted_count": accepted,
            "v1_source_transcription": "AVAILABLE" if road.get("facts") and source_count else "MISSING",
            "v1_historical_reconstruction": (
                "READY_TO_AUDIT" if accepted == source_count and source_count > 0
                and historical_network and actual_road_operation_verified
                else "NOT_VALIDATED"
            ),
            "v2_independent_operations": "NOT_REGISTERED",
            "v3_measured_numeric": "NOT_VALIDATED",
        },
        "F1": {
            "incident_fact_kind": fire.get("incident_facts_status"),
            "exact_building_known": fire.get("coordinates") is not None or fire.get("address_number") is not None,
            "actual_cordon_known": fire.get("actual_cordon") is not None,
            "v1_incident_facts": "AVAILABLE" if fire_review.get("incident_facts") else "MISSING",
            "v1_historical_restriction_reconstruction": "NOT_VALIDATED",
            "v2_independent_operations": "NOT_REGISTERED",
            "v3_measured_numeric": "NOT_VALIDATED",
        },
        "heldout_measured_target_count": len(measured_targets),
        "traffic_source_status": traffic.get("status"),
        "overall_historical_numeric_claim": "NOT_VALIDATED",
        "blocking_evidence": [
            "R1 directed-edge mapping requires independent human acceptance",
            "R1 planned restriction notice does not confirm actual operated closure intervals",
            "F1 actual cordon/road restriction geometry and exact building remain unknown",
            "event-date network/GTFS not validated",
            "independent operational labels not registered",
            "event-matched measured traffic outcomes and controls not registered",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(assess(args.root), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
