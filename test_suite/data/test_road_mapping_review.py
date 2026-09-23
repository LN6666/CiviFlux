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
    for name in (*INPUTS, "evidence/wp1/directed_road_mapping.csv"):
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
