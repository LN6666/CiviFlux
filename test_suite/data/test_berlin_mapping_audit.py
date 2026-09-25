from __future__ import annotations

import pytest

from scripts.berlin_mapping_audit import score_edge
from scripts.berlin_validation_map import _marathon_line_reports, _metric_line


def test_viz_line_supports_position_but_cannot_verify_road_direction() -> None:
    road = [[13.380, 52.520], [13.383, 52.520]]
    report = [("viz-report", _metric_line(road))]
    forward = score_edge(road, report)
    reverse = score_edge(list(reversed(road)), report)
    assert forward["status"] == reverse["status"] == "SPATIAL_SUPPORT_DIRECTION_UNRESOLVED"
    assert forward["direction_verified"] is reverse["direction_verified"] is False


def test_point_proximity_is_insufficient_without_longitudinal_overlap() -> None:
    road = [[13.380, 52.520], [13.383, 52.520]]
    crossing = _metric_line([[13.380, 52.519], [13.380, 52.521]])
    result = score_edge(road, [("crossing", crossing)])
    assert result["nearest_gap_m"] == 0
    assert result["maximum_overlap_m"] < result["required_overlap_m"]
    assert result["status"] == "NO_SUFFICIENT_SPATIAL_OVERLAP"
    assert score_edge(road, [])["status"] == "NO_NAMED_REPORT_IN_SNAPSHOT"
    with pytest.raises(ValueError, match="zero-length"):
        score_edge([[13.38, 52.52], [13.38, 52.52]], [("crossing", crossing)])


def test_viz_point_plus_line_report_keeps_display_line() -> None:
    line = {"type": "LineString", "coordinates": [[13.38, 52.52], [13.39, 52.52]]}
    report = {"type": "Feature", "geometry": {"type": "GeometryCollection", "geometries": [
        {"type": "Point", "coordinates": [13.38, 52.52]}, line,
    ]}, "properties": {"id": "notice-1", "content": "Marathonlauf"}}
    assert _marathon_line_reports([report]) == [{"type": "Feature", "geometry": line, "properties": report["properties"]}]
