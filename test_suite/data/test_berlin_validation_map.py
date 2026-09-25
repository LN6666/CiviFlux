from __future__ import annotations

import pytest

from scripts.berlin_validation_map import _comparison_timing, _receipt_feed_time, compare_snapshots


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
    assert metrics["predicted_edges_without_viz_match"] == 0
    assert metrics["matched_viz_segments"] == 2
    assert metrics["scored_matched_viz_segments"] == 2


def test_snapshot_comparison_does_not_treat_preexisting_zero_speed_as_measured_drop() -> None:
    predicted = [road("prediction", 13.380, 20)]
    features, metrics = compare_snapshots(predicted, [road("x", 13.380, 0, 1)], [road("x", 13.380, 0, 1)])
    assert features[0]["properties"]["change_class"] == "unscored_preexisting_closure"
    assert metrics["scored_segments"] == 0
    assert metrics["precision"] is None


def test_snapshot_comparison_keeps_opposite_direction_separate() -> None:
    prediction = road("prediction", 13.380, 20)
    old_opposite = road("opposite", 13.380, 40)
    old_opposite["geometry"]["coordinates"].reverse()
    opposite = road("opposite", 13.380, 20)
    opposite["geometry"]["coordinates"].reverse()
    features, metrics = compare_snapshots([prediction], [old_opposite], [opposite])
    assert features[0]["properties"]["predicted_overlap"] is False
    assert metrics["miss"] == 1


def test_snapshot_comparison_does_not_score_reidentified_geometry_or_missing_event_segment() -> None:
    predicted = [road("prediction", 13.380, 20)]
    before = [road("changed", 13.380, 40), road("vanished", 13.381, 40), road("moved", 13.382, 40)]
    after = [road("changed", 13.380, 15), road("moved", 13.500, 10)]
    after[0]["geometry"]["coordinates"].reverse()
    features, metrics = compare_snapshots(predicted, before, after)
    by_id = {f["properties"]["unique_id"]: f["properties"] for f in features}
    assert by_id["changed"]["change_class"] == "unscored_geometry_changed"
    assert by_id["vanished"]["change_class"] == "unscored_missing_event"
    assert by_id["vanished"]["predicted_overlap"] is None
    assert by_id["moved"]["change_class"] == "unscored_geometry_moved_out"
    assert metrics["scored_segments"] == 0
    assert metrics["unscored"] == 3
    assert metrics["scored_matched_viz_segments"] == 0
    assert metrics["precision"] is None


def test_duplicate_viz_ids_and_stale_feed_cannot_produce_a_score() -> None:
    predicted = [road("prediction", 13.380, 20)]
    with pytest.raises(ValueError, match="duplicate VIZ unique_id"):
        compare_snapshots(predicted, [road("same", 13.380, 40)] * 2, [road("same", 13.380, 15)])
    receipt = {
        "captured_at_utc": "2026-09-26T06:30:00+00:00",
        "traffic": {"feed_time_stamp": "2026-09-26T06:00:00Z"},
    }
    with pytest.raises(ValueError, match="stale or future-dated"):
        _receipt_feed_time(receipt, "event")
    receipt["traffic"]["feed_time_stamp"] = "2026-09-26T06:29:50Z"
    assert _receipt_feed_time(receipt, "event")[1] == 10


def test_capture_and_feed_both_must_straddle_announced_onset() -> None:
    baseline = {
        "captured_at_utc": "2026-09-26T04:45:00+00:00",
        "traffic": {"feed_time_stamp": "2026-09-26T04:44:55Z"},
    }
    event = {
        "captured_at_utc": "2026-09-26T06:30:00+00:00",
        "traffic": {"feed_time_stamp": "2026-09-26T06:29:55Z"},
    }
    assert _comparison_timing(baseline, event)["event_feed_age_s"] == 5
    event["captured_at_utc"] = "2026-09-26T04:59:30+00:00"
    event["traffic"]["feed_time_stamp"] = "2026-09-26T05:00:10Z"
    with pytest.raises(ValueError, match="capture times"):
        _comparison_timing(baseline, event)
    event["captured_at_utc"] = "2026-09-26T06:30:00+00:00"
    event["traffic"]["feed_time_stamp"] = "2026-09-26T06:29:55Z"
    baseline["captured_at_utc"] = "2026-09-26T04:59:30+00:00"
    baseline["traffic"]["feed_time_stamp"] = "2026-09-26T05:00:10Z"
    with pytest.raises(ValueError, match="feed timestamps"):
        _comparison_timing(baseline, event)
