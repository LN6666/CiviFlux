"""Re-run a frozen Berlin OD probe with only geometry-supported active inputs.

This is a separate post-freeze sensitivity analysis. It never changes the
frozen prediction or treats VIZ announcement lines as operated restrictions.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from urbanimpact.citypack.fetch import sha256_file
from urbanimpact.contracts import CityPack
from urbanimpact.network import Router

from scripts.berlin_mapping_audit import audit
from scripts.berlin_validation_map import CANDIDATES, CITY, PROBE, _validate_snapshot_name


def assess(snapshot_name: str, output: Path) -> dict:
    _validate_snapshot_name(snapshot_name)
    with tempfile.TemporaryDirectory(prefix="civiflux-berlin-mapping-") as directory:
        summary_path = Path(directory) / "summary.json"
        detail_path = Path(directory) / "detail.json"
        mapping_summary = audit(snapshot_name, summary_path, detail_path)
        details = json.loads(detail_path.read_text())
        detail_sha = sha256_file(detail_path)
    candidate_sha = sha256_file(CANDIDATES)
    city_sha = sha256_file(CITY)
    probe_sha = sha256_file(PROBE)
    probe = json.loads(PROBE.read_text())
    candidates = json.loads(CANDIDATES.read_text())
    if (
        details["status"] != "CANDIDATE_SPATIAL_AUDIT_ONLY"
        or details["viz_snapshot"] != snapshot_name
        or details["viz_reports_sha256"] != mapping_summary["viz_reports_sha256"]
        or details["candidate_file_sha256"] != candidate_sha
        or details["citypack_sha256"] != city_sha
        or probe["closure_candidates_sha256"] != candidate_sha
        or probe["citypack_sha256"] != city_sha
        or candidates["citypack_sha256"] != city_sha
    ):
        raise ValueError("mapping audit, frozen probe and source bytes differ")
    if datetime.fromisoformat(mapping_summary["viz_captured_at_utc"]) >= datetime.fromisoformat(probe["announced_upcoming_start"]):
        raise ValueError("mapping audit was captured after the announced incremental onset")
    mapped_cases = {case["case_id"]: case for case in details["cases"]}
    input_cases = {case["id"]: case for case in candidates["cases"]}
    active_id = "berlin-2026-active-17-juni"
    upcoming_id = "berlin-2026-upcoming-unter-den-linden"
    active_all = frozenset(input_cases[active_id]["candidate_directed_edge_ids"])
    upcoming = frozenset(input_cases[upcoming_id]["candidate_directed_edge_ids"])
    audited = mapped_cases[active_id]["edges"]
    if {item["edge_id"] for item in audited} != active_all or len(audited) != len(active_all):
        raise ValueError("active candidate audit is incomplete or duplicated")
    allowed_statuses = {"SPATIAL_SUPPORT_DIRECTION_UNRESOLVED", "NO_SUFFICIENT_SPATIAL_OVERLAP"}
    if any(item["status"] not in allowed_statuses or item["direction_verified"] for item in audited):
        raise ValueError("audit has unexpected status or claims direction verification")
    active_supported = frozenset(
        item["edge_id"] for item in audited if item["status"] == "SPATIAL_SUPPORT_DIRECTION_UNRESOLVED"
    )
    city = CityPack.model_validate_json(CITY.read_bytes())
    index = Router._index(city, probe["vehicle_class"])
    outcomes = []
    for route in probe["routes"]:
        origin, target = route["origin_node"], route["target_node"]
        baseline = Router._search(index, origin, [target], active_supported)[target]
        incremental = Router._search(index, origin, [target], active_supported | upcoming)[target]
        outcomes.append({
            "label": route["label"],
            "baseline_status": baseline["status"],
            "incremental_status": incremental["status"],
            "baseline_same_as_frozen": baseline == route["known_active_candidate_arm"],
            "incremental_same_as_frozen": incremental == route["active_plus_upcoming_candidate_arm"],
            "baseline_freeflow_s": baseline["travel_time_s"],
            "incremental_freeflow_s": incremental["travel_time_s"],
        })
    result = {
        "schema_version": "1.0",
        "status": "SPATIAL_SUPPORT_SUBSET_SENSITIVITY_ONLY",
        "event_id": "berlin-marathon-2026",
        "frozen_probe_sha256": probe_sha,
        "citypack_sha256": city_sha,
        "closure_candidates_sha256": candidate_sha,
        "mapping_detail_sha256": detail_sha,
        "viz_snapshot": snapshot_name,
        "viz_captured_at_utc": mapping_summary["viz_captured_at_utc"],
        "viz_reports_sha256": mapping_summary["viz_reports_sha256"],
        "active_candidate_count": len(active_all),
        "active_geometry_supported_count": len(active_supported),
        "active_without_sufficient_geometry_count": len(active_all - active_supported),
        "upcoming_candidate_count_unchanged": len(upcoming),
        "outcomes": outcomes,
        "all_fixed_od_results_identical": all(
            item["baseline_same_as_frozen"] and item["incremental_same_as_frozen"] for item in outcomes
        ),
        "claim_ceiling": "Post-freeze sensitivity of three declared synthetic OD pairs only. Filtering eight active candidate edges by pre-onset VIZ announcement geometry does not establish the true operated closure set, direction, citywide robustness or observed event impact. The frozen prospective probe is unchanged.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot_name")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/events/berlin-2026-mapping-sensitivity.json")
    args = parser.parse_args()
    print(json.dumps(assess(args.snapshot_name, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
