from types import SimpleNamespace

from urbanimpact.fixtures import toy_city
from urbanimpact.network import compile_restrictions

from scripts.baku_active_indirect_probe import _action_scenario, corridor_candidates


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
