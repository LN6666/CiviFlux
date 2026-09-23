"""Validate human road-mapping decisions against frozen Helsinki candidates.

This checks the identity and completeness of a *submitted* review record. It
cannot establish that the named reviewer is independent or that a planned
restriction actually operated; those require external evidence and review.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROAD_FACT_IDS = frozenset({"R1", "R2", "R3"})
REVIEW_RELATIVE_PATH = Path("evidence/wp1/road_mapping_human_review.json")
REVIEW_FIELDS = frozenset(
    {
        "schema_version",
        "case_id",
        "source_card_sha256",
        "candidate_report_sha256",
        "candidate_csv_sha256",
        "candidate_map_sha256",
        "case_geometry_sha256",
        "reviewer",
        "reviewed_at",
        "facts",
    }
)
FACT_FIELDS = frozenset(
    {
        "fact_id",
        "decision",
        "reviewed_candidate_edge_ids",
        "accepted_directed_edge_ids",
        "source_landmarks_checked",
        "travel_direction_checked",
        "review_note",
    }
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_snapshot(root: Path) -> dict:
    """Bind the review to the source card, generated groups, and row-level CSV."""
    source_path = root / "cases/helsinki_cityrun_2026/case_evidence.json"
    report_path = root / "evidence/wp1/case_review.json"
    csv_path = root / "evidence/wp1/directed_road_mapping.csv"
    map_path = root / "evidence/wp1/directed_road_review.html"
    geometry_path = root / "evidence/wp1/case_geometry.geojson"
    card = json.loads(source_path.read_text())
    report = json.loads(report_path.read_text())
    road = report["road_case"]
    source_hash = _sha256(source_path)
    source_facts = {fact["fact_id"]: fact for fact in card["facts"]}
    groups = {group["fact_id"]: group for group in road["mapping"]}
    if len(source_facts) != len(card["facts"]) or len(groups) != len(road["mapping"]):
        raise ValueError("duplicate source fact or candidate mapping fact ID")
    if road["source_card"]["sha256"] != source_hash:
        raise ValueError("candidate report has a different source card")
    if set(groups) != ROAD_FACT_IDS or not ROAD_FACT_IDS <= set(source_facts):
        raise ValueError("candidate fact IDs do not match the road source card")
    candidates = {}
    for fact_id, group in groups.items():
        ids = group["directed_edge_ids"]
        if not ids or len(ids) != len(set(ids)) or group["source_card_sha256"] != source_hash:
            raise ValueError(f"invalid candidate group for {fact_id}")
        fact = source_facts[fact_id]
        if any(
            group["source_fact"].get(key) != fact.get(key)
            for key in ("road_name", "direction", "from_landmark", "to_landmark", "announced_date_range")
        ):
            raise ValueError(f"candidate group no longer matches source fact {fact_id}")
        candidates[fact_id] = sorted(ids)
    with csv_path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    csv_groups = {fact_id: [] for fact_id in ROAD_FACT_IDS}
    for row in rows:
        if row["fact_id"] not in ROAD_FACT_IDS:
            continue  # F1 is an illustrative fire assumption, never a road-notice review.
        if row["source_card_sha256"] != source_hash:
            raise ValueError("candidate CSV has a different source card")
        csv_groups[row["fact_id"]].append(row["directed_edge_id"])
    if any(sorted(csv_groups[fact_id]) != candidates[fact_id] for fact_id in ROAD_FACT_IDS):
        raise ValueError("candidate CSV and report contain different directed edges")
    return {
        "case_id": card["case_id"],
        "source_card_sha256": source_hash,
        "candidate_report_sha256": _sha256(report_path),
        "candidate_csv_sha256": _sha256(csv_path),
        "candidate_map_sha256": _sha256(map_path),
        "case_geometry_sha256": _sha256(geometry_path),
        "candidates": candidates,
    }


def review_template(root: Path) -> dict:
    """Return a blank, hash-bound form; a template is never accepted as review."""
    snapshot = candidate_snapshot(root)
    return {
        "schema_version": "1.0",
        "case_id": snapshot["case_id"],
        "source_card_sha256": snapshot["source_card_sha256"],
        "candidate_report_sha256": snapshot["candidate_report_sha256"],
        "candidate_csv_sha256": snapshot["candidate_csv_sha256"],
        "candidate_map_sha256": snapshot["candidate_map_sha256"],
        "case_geometry_sha256": snapshot["case_geometry_sha256"],
        "reviewer": {"id": "", "role": "", "independent_of_candidate_generation": False},
        "reviewed_at": "",
        "facts": [
            {
                "fact_id": fact_id,
                "decision": "PENDING",
                "reviewed_candidate_edge_ids": snapshot["candidates"][fact_id],
                "accepted_directed_edge_ids": [],
                "source_landmarks_checked": False,
                "travel_direction_checked": False,
                "review_note": "",
            }
            for fact_id in sorted(ROAD_FACT_IDS)
        ],
    }


def validate_review(root: Path, document: dict) -> dict:
    """Count only complete, source-bound accepted *candidate* mappings."""
    snapshot = candidate_snapshot(root)
    if not isinstance(document, dict) or set(document) != REVIEW_FIELDS:
        raise ValueError("road mapping review has missing or extra fields")
    for field in (
        "case_id",
        "source_card_sha256",
        "candidate_report_sha256",
        "candidate_csv_sha256",
        "candidate_map_sha256",
        "case_geometry_sha256",
    ):
        if document[field] != snapshot[field]:
            raise ValueError(f"road mapping review is stale: {field}")
    if document["schema_version"] != "1.0":
        raise ValueError("unsupported road mapping review version")
    reviewer = document["reviewer"]
    if not isinstance(reviewer, dict) or set(reviewer) != {
        "id",
        "role",
        "independent_of_candidate_generation",
    }:
        raise ValueError("reviewer identity and role are required")
    for field in ("id", "role"):
        if not isinstance(reviewer[field], str) or not 2 <= len(reviewer[field].strip()) <= 128:
            raise ValueError(f"reviewer {field} is required")
    if reviewer["independent_of_candidate_generation"] is not True:
        raise ValueError("reviewer must attest independence from candidate generation")
    try:
        reviewed_at = datetime.fromisoformat(document["reviewed_at"])
    except (AttributeError, ValueError) as exc:
        raise ValueError("reviewed_at must be an ISO 8601 timestamp") from exc
    if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
        raise ValueError("reviewed_at requires an explicit timezone")
    facts = document["facts"]
    if not isinstance(facts, list) or len(facts) != len(ROAD_FACT_IDS):
        raise ValueError("review must cover every motor-road source fact")
    seen = set()
    accepted = []
    unresolved = []
    for fact in facts:
        if not isinstance(fact, dict) or set(fact) != FACT_FIELDS:
            raise ValueError("review fact has missing or extra fields")
        fact_id = fact["fact_id"]
        if fact_id not in ROAD_FACT_IDS or fact_id in seen:
            raise ValueError("review fact ID is missing, duplicated, or unsupported")
        seen.add(fact_id)
        candidates = snapshot["candidates"][fact_id]
        if fact["reviewed_candidate_edge_ids"] != candidates:
            raise ValueError(f"review did not inspect the complete frozen candidate set for {fact_id}")
        chosen = fact["accepted_directed_edge_ids"]
        if (
            not isinstance(chosen, list)
            or any(not isinstance(edge_id, str) for edge_id in chosen)
            or len(chosen) != len(set(chosen))
            or any(edge_id not in candidates for edge_id in chosen)
        ):
            raise ValueError(f"review selected invalid directed edges for {fact_id}")
        if fact["decision"] not in {"ACCEPTED", "REJECTED", "UNRESOLVED"}:
            raise ValueError(f"review decision incomplete for {fact_id}")
        if not isinstance(fact["review_note"], str) or not 8 <= len(fact["review_note"].strip()) <= 2000:
            raise ValueError(f"review note required for {fact_id}")
        if fact["decision"] == "ACCEPTED":
            if (
                not chosen
                or fact["source_landmarks_checked"] is not True
                or fact["travel_direction_checked"] is not True
            ):
                raise ValueError(f"accepted mapping lacks source or direction check for {fact_id}")
            accepted.append(fact_id)
        elif chosen:
            raise ValueError(f"unaccepted fact cannot assert directed edges for {fact_id}")
        if fact["decision"] == "UNRESOLVED":
            unresolved.append(fact_id)
    return {
        "status": "SELF_ATTESTED_HUMAN_REVIEW_REQUIRES_EXTERNAL_IDENTITY_CHECK",
        "accepted_fact_ids": sorted(accepted),
        "accepted_fact_count": len(accepted),
        "unresolved_fact_ids": sorted(unresolved),
        "reviewer_id": reviewer["id"],
        "reviewed_at": document["reviewed_at"],
        "source_card_sha256": snapshot["source_card_sha256"],
        "candidate_csv_sha256": snapshot["candidate_csv_sha256"],
    }
