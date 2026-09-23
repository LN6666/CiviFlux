"""Independent review regression checks. Expected invariants, never xfail/threshold relaxation.

The initial failures establish review findings; production modules are owned by the integrator.
"""

from __future__ import annotations

from collections import deque as RealDeque
from copy import deepcopy
from datetime import datetime

import pytest
from urbanimpact.actions import ActionError, Workspace
from urbanimpact.contracts import ActionRequest, CityPack, Link, OntologyObject, ProjectionSpec
from urbanimpact.fixtures import toy_city, toy_scenario
from urbanimpact.graph import city_objects, paired_projection, project, witness_paths
from urbanimpact.network import Router
from urbanimpact.ranking import RELATION_DEFINITIONS, compare
from urbanimpact.util import digest

from ontology.registry import validate_links


@pytest.fixture
def current_pair():
    city, scenario = toy_city(), toy_scenario()
    policy = {relation: 1.0 for relation in RELATION_DEFINITIONS}
    facts = Router().compare(city, scenario, origins=["A"])
    return paired_projection(city, scenario, facts, digest(policy)), policy


@pytest.mark.parametrize("corruption", ["unregistered_source", "duplicate_source", "cross_type_id"])
def test_imported_citypack_rejects_ambiguous_authoritative_identity(corruption):
    """Importing an immutable snapshot must not accept orphan/ambiguous provenance or object IDs."""
    data = toy_city().model_dump(mode="json")
    if corruption == "unregistered_source":
        data["edges"][0]["source_id"] = "source-that-does-not-exist"
    elif corruption == "duplicate_source":
        data["sources"].append({**data["sources"][0], "sha256": "f" * 64})
    else:
        data["facilities"][0]["id"] = data["edges"][0]["id"]
    with pytest.raises(ValueError):
        CityPack.model_validate(data)


@pytest.mark.parametrize(
    "field,value", [("projection_id", "unregistered-profile"), ("ontology_version", "999.0.0")]
)
def test_project_requires_registered_profile_and_matching_ontology(current_pair, field, value):
    pair, _ = current_pair
    spec = {**pair["baseline"]["spec"], field: value}
    with pytest.raises(ValueError):
        project(city_objects(toy_city()), [], ProjectionSpec.model_validate(spec))


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_snapshot_hash", "f" * 64),
        ("analysis_time", "2026-05-16T11:00:00+03:00"),
        ("objective", "transit_association"),
        ("relation_policy_hash", "f" * 64),
        ("projection_kind", "dependency_evidence"),
    ],
)
def test_delta_ppr_rejects_different_comparison_context(current_pair, field, value):
    pair, policy = deepcopy(current_pair)
    pair["event"]["spec"][field] = value
    with pytest.raises(ValueError):
        compare(pair, ["bc"], policy)


def test_delta_ppr_rejects_unbound_policy(current_pair):
    pair, policy = current_pair
    changed = {**policy, "SEGMENT_ACCESS_TO_FACILITY": 0.01}
    with pytest.raises(ValueError):
        compare(pair, ["bc"], changed)


@pytest.mark.parametrize("corruption", ["graph_payload", "node_hash"])
def test_delta_ppr_verifies_claimed_graph_and_universe_hashes(current_pair, corruption):
    pair, policy = deepcopy(current_pair)
    if corruption == "graph_payload":
        pair["event"]["links"].pop()
    else:
        pair["baseline"]["node_universe_hash"] = pair["event"]["node_universe_hash"] = "f" * 64
    with pytest.raises(ValueError):
        compare(pair, ["bc"], policy)


def test_current_road_links_intersect_edge_and_turn_vehicle_permissions():
    data = toy_city().model_dump(mode="json")
    for edge in data["edges"]:
        if edge["id"] == "bc":
            edge["allowed_vehicle_classes"] = ["bus"]
    city = CityPack.model_validate(data)
    scenario = toy_scenario(closed=())
    policy = {relation: 1.0 for relation in RELATION_DEFINITIONS}
    facts = Router().compare(city, scenario, origins=["A"])
    assert "bc" not in facts["od"][0]["baseline"]["edge_ids"]
    pair = paired_projection(city, scenario, facts, digest(policy))
    for side in ("baseline", "event"):
        assert not [
            link
            for link in pair[side]["links"]
            if link["relation_type"] == "ROAD_CONNECTS_TO" and "bc" in (link["src"], link["dst"])
        ], "Operational graph asserted a legal passenger turn through a bus-only segment"


def test_witness_search_bounds_pending_paths_not_only_completed_visits(monkeypatch):
    """A small layered DAG must not create >10k pending copied paths before its visit budget."""
    import urbanimpact.graph as graph_module

    class BoundedDeque(RealDeque):
        def append(self, item):
            assert len(self) < 10_000, "Witness queue exceeded the declared 10k search budget"
            super().append(item)

    monkeypatch.setattr(graph_module, "deque", BoundedDeque)
    layers = [["seed"]] + [[f"{depth}:{i}" for i in range(40)] for depth in range(3)]
    links = [
        dict(id=f"{source}->{target}", src=source, dst=target, evidence_refs=["synthetic"])
        for first, second in zip(layers, layers[1:])
        for source in first
        for target in second
    ]
    assert witness_paths({"links": links}, ["seed"], "unreachable-target") == []


def test_reversed_typed_facility_link_is_rejected():
    objects = [
        OntologyObject(
            object_id="road",
            object_type="RoadSegment",
            source_namespace="test",
            source_id="synthetic",
            provenance_refs=("synthetic",),
            evidence_level="authoritative/imported",
        ),
        OntologyObject(
            object_id="hospital",
            object_type="Hospital",
            source_namespace="test",
            source_id="synthetic",
            provenance_refs=("synthetic",),
            evidence_level="authoritative/imported",
        ),
    ]
    reverse = Link(
        id="reversed",
        src="hospital",
        dst="road",
        relation_type="SEGMENT_ACCESS_TO_FACILITY",
        evidence_refs=("synthetic",),
        asserted_or_derived="derived",
        derivation_id="review",
        confidence_status="verified",
    )
    with pytest.raises(ValueError):
        validate_links(objects, [reverse])


def test_action_failure_after_candidate_does_not_commit_partial_overlay(tmp_path):
    workspace = Workspace(tmp_path / "atomic.sqlite", toy_city())
    scenario = toy_scenario()
    request = ActionRequest(
        action_id="create",
        action_type="CreateScenario",
        scenario_id=scenario.scenario_id,
        parameters={"scenario": scenario.model_dump(mode="json")},
    )
    with pytest.raises(ValueError):
        # Record validation fails after the candidate write, requiring transaction rollback.
        workspace.commit(request, timestamp=datetime(2026, 1, 1))
    with pytest.raises(ActionError):
        workspace.scenario(scenario.scenario_id)
    assert workspace.history(scenario.scenario_id) == []
    assert digest(workspace.city) == digest(toy_city())


def test_replay_keeps_snapshot_and_overlay_after_rejected_attempt(tmp_path):
    workspace = Workspace(tmp_path / "original.sqlite", toy_city())
    scenario = toy_scenario()
    workspace.commit(
        ActionRequest(
            action_id="create",
            action_type="CreateScenario",
            scenario_id=scenario.scenario_id,
            parameters={"scenario": scenario.model_dump(mode="json")},
        )
    )
    with pytest.raises(ActionError):
        workspace.commit(
            ActionRequest(
                action_id="invalid",
                action_type="ChangeAnalysisPolicy",
                scenario_id=scenario.scenario_id,
                parameters={"ranking": "invented", "objective": "facility_access"},
            )
        )
    replay = workspace.replay(scenario.scenario_id, tmp_path / "replay.sqlite")
    assert digest(replay.scenario(scenario.scenario_id)) == digest(workspace.scenario(scenario.scenario_id))
    assert replay.snapshot_hash == workspace.snapshot_hash == digest(toy_city())


def test_ppr_rejects_infinite_tolerance_instead_of_false_convergence():
    from scipy import sparse
    from urbanimpact.ranking import ppr

    with pytest.raises(ValueError):
        ppr(sparse.csr_matrix([[0.0, 1.0], [1.0, 0.0]]), [1.0, 0.0], tolerance=float("inf"))


@pytest.mark.parametrize("violation", ["audit_object", "typed_direction"])
def test_valid_hashes_do_not_replace_projection_type_validation(current_pair, violation):
    """Hashes provide content integrity, not proof of registry/allowlist conformance."""
    pair, policy = deepcopy(current_pair)
    for side in ("baseline", "event"):
        graph = pair[side]
        if violation == "audit_object":
            extra = {**graph["nodes"][0], "object_id": "z-audit-run", "object_type": "SimulationRun"}
            graph["nodes"].append(extra)
            graph["nodes"].sort(key=lambda item: item["object_id"])
        else:
            link = next(item for item in graph["links"] if item["relation_type"] == "ROAD_CONNECTS_TO")
            link["src"] = "hospital"  # A Hospital does not implement RoadSegment.
        graph["graph_hash"] = digest({"nodes": graph["nodes"], "links": graph["links"]})
        graph["node_universe_hash"] = digest([item["object_id"] for item in graph["nodes"]])
    pair["projection_hash"] = digest({key: value for key, value in pair.items() if key != "projection_hash"})
    with pytest.raises(ValueError):
        compare(pair, ["bc"], policy)


def test_materialized_run_is_bound_to_exact_overlay_and_snapshot():
    from urbanimpact.ontology import materialize

    city, original = toy_city(), toy_scenario()
    changed = toy_scenario(closed=())  # Same ID, different current restrictions.
    run = {
        "run_id": "old-run",
        "scenario_id": original.scenario_id,
        "citypack_id": city.citypack_id,
        "source_snapshot_hash": digest(city),
        "scenario_overlay_hash": digest(original),
        "simulation_status": "not_requested",
    }
    with pytest.raises(ValueError):
        materialize(city, changed, run)


def test_fire_assumption_links_keep_assumed_confidence_and_valid_time():
    from urbanimpact.ontology import materialize

    scenario = toy_scenario(kind="fire")
    _, links = materialize(toy_city(), scenario)
    impacts = [link for link in links if link.relation_type.value == "INCIDENT_RESTRICTS"]
    assert impacts
    restriction = scenario.restrictions[0]
    for link in impacts:
        assert link.confidence_status == "assumed"
        assert link.valid_time.valid_from == restriction.valid_from
        assert link.valid_time.valid_to == restriction.valid_to
