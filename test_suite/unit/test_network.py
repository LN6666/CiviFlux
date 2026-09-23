from datetime import datetime, timedelta, timezone
from itertools import permutations

import pytest
from pydantic import ValidationError
from urbanimpact.contracts import CityPack, Scenario
from urbanimpact.network import Router, compare_boundaries, compile_restrictions

T = datetime(2026, 1, 1, tzinfo=timezone.utc)


def city(edges=None, connections=None):
    specs = edges or [
        ("ab", "A", "B", 1),
        ("bc", "B", "C", 1),
        ("ad", "A", "D", 3),
        ("dc", "D", "C", 3),
        ("ch", "C", "H", 1),
    ]
    return CityPack.model_validate(
        dict(
            citypack_id="fixture",
            network_temporality="synthetic",
            transit_temporality="unavailable",
            sources=[
                dict(id="s", url="synthetic", sha256="0" * 64, retrieved_at=T.isoformat(), license="CC0")
            ],
            nodes=[
                dict(id=n, lon=i / 1000, lat=0)
                for i, n in enumerate(sorted({n for _, a, b, _ in specs for n in (a, b)}))
            ],
            edges=[
                dict(
                    id=e,
                    source=a,
                    target=b,
                    length_m=cost * 10,
                    speed_kph=36,
                    allowed_vehicle_classes=["passenger", "emergency"],
                    source_id="s",
                    external_id=e,
                )
                for e, a, b, cost in specs
            ],
            connections=connections,
            facilities=[
                dict(
                    id="hospital",
                    type="Hospital",
                    name="H",
                    lon=0,
                    lat=0,
                    entrance_node_id="H",
                    source_id="s",
                    external_id="H",
                    access_status="verified",
                ),
                dict(
                    id="unknown",
                    type="Facility",
                    name="Unknown",
                    lon=0,
                    lat=0,
                    entrance_node_id=None,
                    source_id="s",
                    external_id="missing",
                    access_status="unknown",
                ),
            ],
        )
    )


def scenario(edge="bc", start=T, end=T + timedelta(hours=1), at=T):
    return Scenario.model_validate(
        dict(
            scenario_id="event",
            citypack_id="fixture",
            kind="road",
            analysis_at=at,
            window=dict(start=T - timedelta(hours=1), end=T + timedelta(hours=2)),
            seed_spec=dict(entity_ids=["A"]),
            restrictions=[]
            if edge is None
            else [
                dict(
                    id="r",
                    edge_ids=[edge],
                    valid_from=start,
                    valid_to=end,
                    blocked_classes=["passenger"],
                    evidence_kind="announced",
                    evidence_refs=["s"],
                )
            ],
        )
    )


def test_hand_solved_and_unknown_entrance():
    result = Router().compare(city(), scenario())
    assert result["all_facilities_checked"] == 2
    row = result["od"][0]
    assert row["baseline"]["travel_time_s"] == 3
    assert row["event"]["travel_time_s"] == 7
    assert row["event"]["edge_ids"] == ["ad", "dc", "ch"]
    assert result["od"][1]["event"]["status"] == "unavailable"
    assert result["od"][1]["event"]["travel_time_s"] is None
    assert Router().compare(city(), scenario(None))["od"][0]["delta_travel_time_s"] == 0


def test_unique_bridge_unreachable_is_not_zero_and_direction():
    row = Router().compare(city(), scenario("ch"))["od"][0]
    assert row["event"]["status"] == "unreachable"
    assert row["event"]["travel_time_s"] is None
    assert Router().route(city(), "H", "A")["status"] == "unreachable"
    assert Router().route(city(), "H", "H")["travel_time_s"] == 0


def test_half_open_window_and_class():
    s = scenario()
    assert compile_restrictions(city(), s, at=T) == {"bc"}
    assert not compile_restrictions(city(), s, at=s.restrictions[0].valid_to)
    assert not compile_restrictions(city(), s, at=T - timedelta(microseconds=1))
    assert not compile_restrictions(city(), s, "emergency")
    with pytest.raises(ValueError, match="Unknown restriction"):
        compile_restrictions(city(), scenario("ghost", start=T + timedelta(minutes=1)))
    with pytest.raises(ValueError, match="Unknown vehicle"):
        compile_restrictions(city(), s, "flying")
    with pytest.raises(ValidationError):
        s.restrictions[0].model_validate({**s.restrictions[0].model_dump(), "blocked_classes": ["flying"]})


def test_turn_state_not_node_and_no_invented_emergency_permission():
    c = city(
        connections=[
            dict(from_edge=a, to_edge=b, allowed_vehicle_classes=["passenger"])
            for a, b in [("ab", "bc"), ("ad", "dc"), ("dc", "ch")]
        ]
    )
    assert Router().route(c, "A", "H")["edge_ids"] == ["ad", "dc", "ch"]
    assert Router().route(c, "A", "H", "emergency")["status"] == "unreachable"
    c = c.model_copy(
        update={
            "edges": tuple(e.model_copy(update={"allowed_vehicle_classes": ("passenger",)}) for e in c.edges)
        }
    )
    assert Router().route(c, "A", "H", "emergency")["status"] == "unreachable"


def test_parallel_edge_and_planar_crossing_are_not_inferred_connections():
    c = city([("ab", "A", "B", 1), ("ab2", "A", "B", 2), ("bh", "B", "H", 1), ("cd", "C", "D", 1)])
    assert Router().route(c, "A", "H", blocked=["ab"])["edge_ids"] == ["ab2", "bh"]
    assert Router().route(c, "C", "H")["status"] == "unreachable"


def exhaustive_oracle(c, start, target, forbidden):
    """Enumerate simple edge paths independently of router data structures."""
    lengths = []

    def visit(node, used, cost):
        if node == target:
            lengths.append(cost)
            return
        for edge in c.edges:
            if edge.source == node and edge.id not in used and edge.id not in forbidden:
                visit(edge.target, used | {edge.id}, cost + edge.length_m / (edge.speed_kph / 3.6))

    visit(start, set(), 0)
    return min(lengths) if lengths else None


def test_all_edge_deletion_pairs_against_independent_oracle():
    c = city()
    base = Router().route(c, "A", "H")["travel_time_s"]
    for forbidden in [(), *((e.id,) for e in c.edges), *permutations([e.id for e in c.edges], 2)]:
        observed = Router().route(c, "A", "H", blocked=forbidden)["travel_time_s"]
        assert observed == exhaustive_oracle(c, "A", "H", set(forbidden))
        assert observed is None or observed >= base


def test_expanded_crop_keeps_outer_detour():
    outer = city()
    inner = outer.model_copy(update={"edges": tuple(e for e in outer.edges if e.id not in ("ad", "dc"))})
    evidence = compare_boundaries(inner, outer, scenario(), ["A"], threshold_seconds=1)
    assert evidence["status"] == "not_stable"
    assert evidence["differences"][0]["stage"] == "event"
    assert compare_boundaries(outer, outer, scenario(), ["A"])["status"] == "stable"


def test_transit_geometry_remains_candidate_and_never_delay():
    c = city().model_copy(
        update={
            "transit": {
                "shape_matches": [
                    {
                        "shape_id": "s",
                        "route_ids": ["bus-1"],
                        "candidate_edge_ids": ["bc"],
                        "status": "candidate",
                        "truncated": True,
                    }
                ]
            }
        }
    )
    result = Router().compare(c, scenario())
    assert result["transit"][0]["match_status"] == "candidate"
    assert result["transit"][0]["candidates_truncated"] is True
    assert "delay_s" not in result["transit"][0]


def test_verified_route_association_does_not_invent_bus_permission_restriction():
    c = city().model_copy(
        update={
            "transit": {
                "routes": [{"id": "bus-1", "edge_ids": ["ab", "bc", "ch"], "match_status": "verified"}]
            }
        }
    )
    associated = Router().compare(c, scenario())["transit"][0]
    assert associated["match_status"] == "verified"
    assert associated["bus_permission_affected"] is False
