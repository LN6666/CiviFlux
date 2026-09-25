"""Triangulate Berlin notice-to-road candidates against a saved VIZ report snapshot.

The VIZ line is another announced-closure geometry, not field execution. An
overlap can aid human review but cannot approve a directed restriction edge.
Road-level report data and detailed matches stay in the ignored raw directory.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from shapely.geometry import LineString

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.berlin_validation_map import (
    CANDIDATES,
    CITY,
    RAW,
    ROOT,
    _metric_line,
    _validate_snapshot_name,
    build,
    sha256_file,
)

MATCH_BUFFER_M = 18


def score_edge(coordinates: list[list[float]], report_lines: list[tuple[str, LineString]]) -> dict:
    """Use length of road inside a VIZ line buffer; direction stays unknown."""
    road = _metric_line(coordinates)
    if road.length <= 0:
        raise ValueError("candidate road has zero-length geometry")
    threshold = min(road.length * 0.25, 25.0)
    if not report_lines:
        return {
            "status": "NO_NAMED_REPORT_IN_SNAPSHOT",
            "nearest_report_id": None,
            "nearest_gap_m": None,
            "maximum_overlap_m": 0.0,
            "required_overlap_m": round(threshold, 3),
            "direction_verified": False,
        }
    measured = [(report_id, road.distance(line), road.intersection(line.buffer(MATCH_BUFFER_M)).length)
                for report_id, line in report_lines]
    nearest = min(measured, key=lambda item: (item[1], item[0]))
    overlap = max(item[2] for item in measured)
    return {
        "status": "SPATIAL_SUPPORT_DIRECTION_UNRESOLVED" if overlap >= threshold else "NO_SUFFICIENT_SPATIAL_OVERLAP",
        "nearest_report_id": nearest[0],
        "nearest_gap_m": round(nearest[1], 3),
        "maximum_overlap_m": round(overlap, 3),
        "required_overlap_m": round(threshold, 3),
        "direction_verified": False,
    }


def audit(snapshot_name: str, summary_path: Path, detail_path: Path, map_path: Path | None = None) -> dict:
    _validate_snapshot_name(snapshot_name)
    receipt = json.loads((RAW / f"{snapshot_name}-receipt.json").read_text())
    reports_path = ROOT / receipt["reports"]["local_path"]
    if reports_path.resolve() != (RAW / f"{snapshot_name}-reports.json").resolve():
        raise ValueError("report receipt path differs from immutable snapshot name")
    if sha256_file(reports_path) != receipt["reports"]["sha256"]:
        raise ValueError("report bytes changed after capture")
    raw = json.loads(reports_path.read_text())
    if raw.get("type") != "FeatureCollection" or len(raw.get("features", [])) != receipt["reports"]["feature_count"]:
        raise ValueError("report collection differs from capture receipt")
    candidates = json.loads(CANDIDATES.read_text())
    if candidates["citypack_sha256"] != sha256_file(CITY):
        raise ValueError("candidate roads no longer match the pinned CityPack")
    wanted = {edge_id for case in candidates["cases"] for edge_id in case["candidate_directed_edge_ids"]}
    city = json.loads(CITY.read_text())
    edges = {edge["id"]: edge for edge in city["edges"] if edge["id"] in wanted}
    if len(edges) != len(wanted):
        raise ValueError("candidate edge missing from pinned CityPack")
    reports = []
    for feature in raw["features"]:
        props = feature.get("properties", {})
        if props.get("subtype") != "Sperrung" or "marathon" not in str(props.get("content", "")).lower():
            continue
        geometries = feature.get("geometry", {}).get("geometries", [])
        lines = [
            (props["id"], _metric_line(geometry["coordinates"]))
            for geometry in geometries if geometry.get("type") == "LineString"
        ]
        if lines:
            reports.append({"id": props["id"], "street": str(props.get("street", "")), "lines": lines})
    summary_cases, detail_cases = [], []
    for case in candidates["cases"]:
        named = [report for report in reports if case["street"].casefold() in report["street"].casefold()]
        lines = [line for report in named for line in report["lines"]]
        details = []
        for edge_id in case["candidate_directed_edge_ids"]:
            result = score_edge(edges[edge_id]["geometry"], lines)
            details.append({"edge_id": edge_id, "length_m": edges[edge_id]["length_m"], **result})
        gaps = [item["nearest_gap_m"] for item in details if item["nearest_gap_m"] is not None]
        supported = sum(item["status"] == "SPATIAL_SUPPORT_DIRECTION_UNRESOLVED" for item in details)
        summary_cases.append({
            "case_id": case["id"],
            "role": case["prediction_role"],
            "candidate_directed_edges": len(details),
            "same_street_viz_reports": len(named),
            "within_18_m": sum(gap <= MATCH_BUFFER_M for gap in gaps),
            "sufficient_overlap": supported,
            "without_sufficient_overlap": len(details) - supported,
            "supported_directed_length_m": round(sum(item["length_m"] for item in details if item["status"] == "SPATIAL_SUPPORT_DIRECTION_UNRESOLVED"), 1),
            "unsupported_directed_length_m": round(sum(item["length_m"] for item in details if item["status"] != "SPATIAL_SUPPORT_DIRECTION_UNRESOLVED"), 1),
            "median_nearest_gap_m": round(statistics.median(gaps), 3) if gaps else None,
            "maximum_nearest_gap_m": round(max(gaps), 3) if gaps else None,
            "direction_verified": 0,
        })
        detail_cases.append({"case_id": case["id"], "named_report_ids": [report["id"] for report in named], "edges": details})
    shared = {
        "schema_version": "1.0",
        "status": "CANDIDATE_SPATIAL_AUDIT_ONLY",
        "event_id": "berlin-marathon-2026",
        "notice_source_id": candidates["source_id"],
        "candidate_file_sha256": sha256_file(CANDIDATES),
        "citypack_sha256": sha256_file(CITY),
        "viz_snapshot": snapshot_name,
        "viz_captured_at_utc": receipt["captured_at_utc"],
        "viz_reports_sha256": receipt["reports"]["sha256"],
        "viz_report_features": receipt["reports"]["feature_count"],
        "marathon_line_reports": len(reports),
        "match_rule": "Case street name must appear in VIZ report street; OSM directed edge must have at least min(25 m, 25% edge length) inside an 18 m buffer of one VIZ report line. VIZ report line has no road-direction approval.",
        "claim_ceiling": "VIZ report lines are scheduled/announced closure geometry, not observed field execution. Spatial support does not verify direction, permissions, validity times or physical impacts; absent support in this snapshot does not disprove the notice. All 72 candidate edges remain CANDIDATE_UNREVIEWED.",
    }
    summary = {**shared, "cases": summary_cases}
    detail = {**shared, "cases": detail_cases}
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    detail_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    detail_path.write_text(json.dumps(detail, ensure_ascii=False, indent=2) + "\n")
    if map_path is not None:
        build(snapshot_name, map_path)
        bundle = json.loads(map_path.read_text())
        by_edge = {item["edge_id"]: item for case in detail_cases for item in case["edges"]}
        for feature in bundle["layers"]["restriction_inputs"]["features"]:
            result = by_edge[feature["properties"]["id"]]
            feature["properties"].update({
                "viz_mapping_status": result["status"],
                "viz_nearest_gap_m": result["nearest_gap_m"],
                "viz_maximum_overlap_m": result["maximum_overlap_m"],
                "viz_required_overlap_m": result["required_overlap_m"],
            })
        bundle["mapping_audit"] = summary
        bundle["comparison_note"] = (
            "Colored restriction candidates have only a pre-event VIZ report geometry cross-check. "
            "Direction, actual closure operation and traffic impacts remain unverified."
        )
        map_path.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot_name")
    parser.add_argument("--summary-output", type=Path, default=ROOT / "evidence/events/berlin-2026-viz-mapping-audit.json")
    parser.add_argument("--detail-output", type=Path, default=RAW / "berlin-2026-viz-mapping-detail.json")
    parser.add_argument("--map-output", type=Path, default=ROOT / "web/public/validation/berlin-mapping-review-local.json")
    args = parser.parse_args()
    print(json.dumps(audit(args.snapshot_name, args.summary_output, args.detail_output, args.map_output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
