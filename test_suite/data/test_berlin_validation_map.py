from __future__ import annotations

import pytest

from scripts.berlin_validation_map import compare_snapshots


def road(key: str, x: float, speed: float, closed: int = 0) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[x, 52.52], [x + 0.001, 52.52]]},
        "properties": {"unique_id": key, "speedavg": speed, "closed": closed},
    }


def test_snapshot_comparison_separates_hits_misses_false_alarms_and_missing() -> None:
    predicted = [road("prediction", 13.380, 20), road("prediction2", 13.383, 20)]
    before = [road("hit", 13.380, 40), road("false", 13.383, 40), road("miss", 13.390, 40), road("closed", 13.392, 0, 1)]
    after = [road("hit", 13.380, 20), road("false", 13.383, 38), road("miss", 13.390, 0, 1), road("closed", 13.392, 0, 1), road("missing", 13.394, 15)]
    features, metrics = compare_snapshots(predicted, before, after)
    by_id = {f["properties"]["unique_id"]: f["properties"] for f in features}
    assert by_id["hit"]["verdict"] == "hit"
    assert by_id["false"]["verdict"] == "false_alarm"
    assert by_id["miss"]["verdict"] == "miss"
    assert by_id["closed"]["verdict"] == "unscored"
    assert by_id["missing"]["verdict"] == "unscored"
    assert metrics["precision"] == pytest.approx(0.5)
    assert metrics["recall"] == pytest.approx(0.5)
    assert metrics["unscored"] == 2
    assert metrics["predicted_edge_count"] == 2
    assert metrics["predicted_edges_with_viz_match"] == 2


def test_snapshot_comparison_does_not_treat_preexisting_zero_speed_as_measured_drop() -> None:
    predicted = [road("prediction", 13.380, 20)]
    features, metrics = compare_snapshots(predicted, [road("x", 13.380, 0, 1)], [road("x", 13.380, 0, 1)])
    assert features[0]["properties"]["change_class"] == "unscored_preexisting_closure"
    assert metrics["scored_segments"] == 0
    assert metrics["precision"] is None


def test_snapshot_comparison_keeps_opposite_direction_separate() -> None:
    prediction = road("prediction", 13.380, 20)
    opposite = road("opposite", 13.380, 20)
    opposite["geometry"]["coordinates"].reverse()
    features, metrics = compare_snapshots([prediction], [road("opposite", 13.380, 40)], [opposite])
    assert features[0]["properties"]["predicted_overlap"] is False
    assert metrics["miss"] == 1
