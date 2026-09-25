from types import SimpleNamespace

from urbanimpact.fixtures import toy_city
from urbanimpact.network import compile_restrictions

from scripts.baku_active_indirect_probe import (
    _action_scenario,
    corridor_candidates,
    pedestrian_area_exposure,
)


def test_declared_buffer_controls_candidate_exposure():
    motor = SimpleNamespace(id="motor", geometry=((49.854, 40.374), (49.855, 40.374)))
    close = SimpleNamespace(id="close", geometry=motor.geometry)
    nearby = SimpleNamespace(id="nearby", geometry=((49.854, 40.37405), (49.855, 40.37405)))
    remote = SimpleNamespace(id="remote", geometry=((49.854, 40.3745), (49.855, 40.3745)))
    city = SimpleNamespace(edges=(remote, nearby, close))
    assert [e.id for e in corridor_candidates(city, [motor], 0.2)] == ["close"]
    assert [e.id for e in corridor_candidates(city, [motor], 15)] == ["close", "nearby"]


def test_hypothetical_active_restriction_is_typed_and_replayable():
    city = toy_city()
    card = {
        "analysis_at": "2026-09-25T12:00:00+04:00",
        "window_start": "2026-09-25T11:00:00+04:00",
        "window_end": "2026-09-25T13:00:00+04:00",
        "restriction_assumption": "Hypothetical walking closure, not a sourced event fact.",
    }
    scenario, actions = _action_scenario(city, "pedestrian", ["bc"], card, "fixture")
    assert [a["record"]["status"] for a in actions] == ["committed", "committed"]
    assert scenario.restrictions[0].evidence_kind == "assumed"
    assert compile_restrictions(city, scenario, "pedestrian") == {"bc"}
    assert compile_restrictions(city, scenario, "passenger") == set()


def test_pedestrian_area_proxy_counts_only_positive_polygon_overlap():
    motor = SimpleNamespace(id="motor", geometry=((49.854, 40.374), (49.855, 40.374)))

    def area(area_id, south, north):
        return {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [49.8542, south],
                        [49.8548, south],
                        [49.8548, north],
                        [49.8542, north],
                        [49.8542, south],
                    ]
                ],
            },
            "properties": {"id": area_id, "source_id": "fixture", "layer": "pedestrian_area"},
        }

    areas = [area("near", 40.37404, 40.37408), area("far", 40.3744, 40.3745)]
    narrow, narrow_features = pedestrian_area_exposure(areas, [motor], 0.2)
    broad, broad_features = pedestrian_area_exposure(areas, [motor], 15)
    assert narrow["candidate_polygons_scanned"] == broad["candidate_polygons_scanned"] == 2
    assert narrow["overlapping_polygons"] == 0 and narrow_features == []
    assert narrow["nearest_polygon_gap_m"] is not None and narrow["nearest_polygon_gap_m"] > 0
    assert broad["overlapping_polygons"] == 1
    assert broad["nearest_polygon_gap_m"] == 0
    assert broad["unique_overlap_area_m2"] > 0
    assert [feature["properties"]["id"] for feature in broad_features] == ["near"]
    assert broad_features[0]["properties"]["evidence_status"] == "GEOMETRIC_OVERLAP_NOT_OBSERVED_CLOSURE"
