"""A generated count or stale candidate list must not become human acceptance."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from urbanimpact.citypack.mapping_review import (
    REVIEW_RELATIVE_PATH,
    candidate_snapshot,
    review_template,
    validate_review,
)

from scripts.historical_backtest_preflight import INPUTS, assess

ROOT = Path(__file__).resolve().parents[2]


def frozen_review_root(tmp_path: Path) -> Path:
    for name in (
        *INPUTS,
        "evidence/wp1/directed_road_mapping.csv",
        "evidence/wp1/directed_road_review.html",
        "evidence/wp1/case_geometry.geojson",
    ):
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    return tmp_path


def completed_review(root: Path) -> dict:
    document = review_template(root)
    document["reviewer"] = {
        "id": "independent-reviewer-example",
        "role": "road-network specialist",
        "independent_of_candidate_generation": True,
    }
    document["reviewed_at"] = "2026-09-24T12:00:00+03:00"
    for fact in document["facts"]:
        fact["decision"] = "ACCEPTED"
        fact["accepted_directed_edge_ids"] = fact["reviewed_candidate_edge_ids"][:1]
        fact["source_landmarks_checked"] = True
        fact["travel_direction_checked"] = True
        fact["review_note"] = "Synthetic test of a complete reviewed candidate set."
    return document


def test_generated_template_cannot_count_as_review(tmp_path: Path) -> None:
    root = frozen_review_root(tmp_path)
    assert set(candidate_snapshot(root)["candidates"]) == {"R1", "R2", "R3"}
    with pytest.raises(ValueError, match="reviewer id"):
        validate_review(root, review_template(root))


def test_pending_fact_cannot_pass_with_reviewer_fields_filled(tmp_path: Path) -> None:
    root = frozen_review_root(tmp_path)
    document = completed_review(root)
    document["facts"][0]["decision"] = "PENDING"
    with pytest.raises(ValueError, match="decision incomplete"):
        validate_review(root, document)


def test_self_reported_count_is_ignored_without_review_record(tmp_path: Path) -> None:
    root = frozen_review_root(tmp_path)
    report_path = root / "evidence/wp1/case_review.json"
    report = json.loads(report_path.read_text())
    report["road_case"]["human_accepted_mapping_count"] = 3
    report_path.write_text(json.dumps(report))
    result = assess(root)
    assert result["R1"]["human_accepted_count"] == 0
    assert result["R1"]["generated_case_report_count_ignored"] == 3
    assert result["R1"]["human_acceptance_basis"]["status"] == "NOT_SUBMITTED"
    assert result["R1"]["v1_historical_reconstruction"] == "NOT_VALIDATED"


def test_complete_review_record_counts_only_bounded_candidate_decisions(tmp_path: Path) -> None:
    root = frozen_review_root(tmp_path)
    document = completed_review(root)
    review_path = root / REVIEW_RELATIVE_PATH
    review_path.write_text(json.dumps(document))
    result = assess(root)
    assert result["R1"]["human_accepted_count"] == 3
    assert result["R1"]["human_acceptance_basis"]["accepted_fact_ids"] == ["R1", "R2", "R3"]
    assert result["R1"]["human_acceptance_basis"]["status"].startswith("SELF_ATTESTED")
    assert str(REVIEW_RELATIVE_PATH) in result["input_sha256"]
    # Planned notice, later network and unknown operating hours still block V1b.
    assert result["R1"]["v1_historical_reconstruction"] == "NOT_VALIDATED"
    assert "R1 directed-edge mapping requires independent human acceptance" not in result["blocking_evidence"]
    assert (
        "R1 submitted reviewer identity and independence require external confirmation"
        in result["blocking_evidence"]
    )


@pytest.mark.parametrize(
    "change, message",
    [
        ("source_hash", "stale"),
        ("missing_candidate", "complete frozen candidate"),
        ("foreign_edge", "invalid directed edges"),
        ("no_direction_check", "direction check"),
        ("no_independence", "independence"),
        ("naive_time", "timezone"),
    ],
)
def test_incomplete_or_stale_review_rejected(tmp_path: Path, change: str, message: str) -> None:
    root = frozen_review_root(tmp_path)
    document = completed_review(root)
    fact = document["facts"][0]
    if change == "source_hash":
        document["source_card_sha256"] = "0" * 64
    elif change == "missing_candidate":
        fact["reviewed_candidate_edge_ids"].pop()
    elif change == "foreign_edge":
        fact["accepted_directed_edge_ids"] = ["not-a-frozen-candidate"]
    elif change == "no_direction_check":
        fact["travel_direction_checked"] = False
    elif change == "no_independence":
        document["reviewer"]["independent_of_candidate_generation"] = False
    else:
        document["reviewed_at"] = "2026-09-24T12:00:00"
    with pytest.raises(ValueError, match=message):
        validate_review(root, document)


def test_review_invalidated_when_generated_candidates_change(tmp_path: Path) -> None:
    root = frozen_review_root(tmp_path)
    document = completed_review(root)
    report_path = root / "evidence/wp1/case_review.json"
    report = json.loads(report_path.read_text())
    report["road_case"]["mapping"][0]["directed_edge_ids"].pop()
    report_path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="candidate CSV and report"):
        validate_review(root, document)


@pytest.mark.parametrize(
    "artifact",
    ["evidence/wp1/directed_road_review.html", "evidence/wp1/case_geometry.geojson"],
)
def test_review_invalidated_when_review_surface_changes(tmp_path: Path, artifact: str) -> None:
    root = frozen_review_root(tmp_path)
    document = completed_review(root)
    path = root / artifact
    path.write_bytes(path.read_bytes() + b"\n ")
    with pytest.raises(ValueError, match="stale"):
        validate_review(root, document)


@pytest.mark.parametrize("duplicate_in", ["source", "candidate"])
def test_duplicate_fact_ids_are_not_silently_collapsed(tmp_path: Path, duplicate_in: str) -> None:
    root = frozen_review_root(tmp_path)
    if duplicate_in == "source":
        path = root / "cases/helsinki_cityrun_2026/case_evidence.json"
        value = json.loads(path.read_text())
        value["facts"].append(value["facts"][0].copy())
    else:
        path = root / "evidence/wp1/case_review.json"
        value = json.loads(path.read_text())
        value["road_case"]["mapping"].append(value["road_case"]["mapping"][0].copy())
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="duplicate source fact or candidate mapping"):
        candidate_snapshot(root)


def test_generated_operation_and_network_flags_cannot_claim_historical_reconstruction(
    tmp_path: Path,
) -> None:
    root = frozen_review_root(tmp_path)
    (root / REVIEW_RELATIVE_PATH).write_text(json.dumps(completed_review(root)))
    report_path = root / "evidence/wp1/case_review.json"
    report = json.loads(report_path.read_text())
    report["road_case"]["observed_operation_verified"] = True
    report_path.write_text(json.dumps(report))
    missing_path = root / "evidence/wp1/missing_data_report.json"
    missing = json.loads(missing_path.read_text())
    missing["historical_network"] = "VALIDATED_EVENT_DATE"
    missing_path.write_text(json.dumps(missing))
    # The submitted review is bound to the original report and must be reissued.
    with pytest.raises(ValueError, match="stale"):
        assess(root)
    (root / REVIEW_RELATIVE_PATH).write_text(json.dumps(completed_review(root)))
    result = assess(root)
    assert result["R1"]["generated_operation_flag_ignored"] is True
    assert result["citypack"]["generated_network_status_ignored"] is True
    assert result["R1"]["actual_operated_restriction_verified"] is False
    assert result["citypack"]["historical_network_ready"] is False
    assert result["R1"]["v1_historical_reconstruction"] == "NOT_VALIDATED"
