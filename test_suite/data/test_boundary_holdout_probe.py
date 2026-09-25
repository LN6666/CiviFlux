"""Focused checks for the deterministic, outcome-independent held-out probe."""

from types import SimpleNamespace

import pytest
from urbanimpact.contracts import Node

from scripts.boundary_holdout_probe import compare_od, select_origins


def _graph(nodes):
    return SimpleNamespace(
        nodes=tuple(nodes),
        edges=tuple(
            SimpleNamespace(
                source=node.id,
                target=node.id,
                allowed_vehicle_classes=("passenger",),
            )
            for node in nodes
        ),
    )


def _row(origin, status, time, path):
    route = {
        "status": status,
        "travel_time_s": time,
        "distance_m": time,
        "edge_ids": path,
    }
    return {"origin": origin, "facility_id": "facility:1", "target": "node:target", "baseline": route, "event": route}


def test_heldout_origin_selection_is_stratified_deterministic_and_excludes_case_nodes():
    nodes = [
        Node(id=f"node:{quadrant}:{index}", lon=lon, lat=lat)
        for quadrant, lon, lat in (
            ("SW", 0.2, 0.2),
            ("SE", 0.8, 0.2),
            ("NW", 0.2, 0.8),
            ("NE", 0.8, 0.8),
        )
        for index in range(3)
    ]
    graph = _graph(nodes)
    excluded = {"node:SW:0", "node:NE:2"}
    first = select_origins(graph, graph, [0, 0, 1, 1], excluded)
    second = select_origins(graph, graph, [0, 0, 1, 1], excluded)
    assert first == second
    assert len(first) == 8
    assert {item["quadrant"] for item in first} == {"SW", "SE", "NW", "NE"}
    assert {item["node_id"] for item in first}.isdisjoint(excluded)
    assert all(sum(item["quadrant"] == quadrant for item in first) == 2 for quadrant in ("SW", "SE", "NW", "NE"))


def test_heldout_probe_reports_status_and_time_changes_without_imputing_missing_metrics():
    outer = [_row("origin:a", "available", 2.0, ["edge:a"]), _row("origin:b", "unreachable", None, [])]
    further = [_row("origin:a", "available", 3.5, ["edge:b"]), _row("origin:b", "available", 4.0, ["edge:c"])]
    result = compare_od(outer, further)
    assert result["od_count"] == 2
    assert result["stage_comparisons"] == 4
    assert result["difference_count"] == 4
    assert {item["reason"] for item in result["differences"]} == {
        "status_changed",
        "travel_time_changed_gt_1s",
    }
    assert result["path_changed_when_both_available_count"] == 2
    assert result["observed_metric_stability"] is False
    outer[1]["baseline"]["travel_time_s"] = 0.0
    with pytest.raises(ValueError, match="imputed"):
        compare_od(outer, further)
