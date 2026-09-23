import copy
import networkx as nx
import numpy as np
import pytest
from scipy import sparse
from urbanimpact.fixtures import toy_city, toy_scenario
from urbanimpact.network import Router
from urbanimpact.graph import paired_projection, project, city_objects
from urbanimpact.contracts import ProjectionSpec, MANIFEST
from urbanimpact.ranking import transition, ppr, compare, RELATION_DEFINITIONS
from urbanimpact.util import digest


@pytest.fixture
def pair():
    city = toy_city()
    scenario = toy_scenario()
    return paired_projection(
        city,
        scenario,
        Router().compare(city, scenario, origins=["A"]),
        digest({t: 1 for t in RELATION_DEFINITIONS}),
    )


def test_dense_and_networkx_independent_oracles(pair):
    g = pair["baseline"]
    matrix = transition(g, {t: 1 for t in RELATION_DEFINITIONS})
    n = matrix.shape[0]
    seed = np.zeros(n)
    seed[0] = 1
    result = ppr(matrix, seed)
    dense = matrix.toarray()
    dense[dense.sum(axis=1) == 0] = seed
    exact = np.linalg.solve(np.eye(n) - 0.85 * dense.T, 0.15 * seed)
    assert np.allclose(result["scores"], exact, atol=1e-11, rtol=0)
    nxg = nx.from_scipy_sparse_array(matrix, create_using=nx.DiGraph)
    oracle = nx.pagerank(
        nxg,
        alpha=0.85,
        personalization=dict(enumerate(seed)),
        dangling=dict(enumerate(seed)),
        tol=1e-14,
        max_iter=3000,
    )
    assert np.allclose(result["scores"], [oracle[i] for i in range(n)], atol=1e-11, rtol=0)
    assert result["mass_error"] < 1e-10 and result["residual_l1"] < 1e-10


def test_pair_keeps_closed_assets_and_real_witnesses(pair):
    result = compare(pair, ["bc"], {t: 1 for t in RELATION_DEFINITIONS})
    assert abs(result["delta_sum"]) < 1e-10
    assert "bc" in [o["object_id"] for o in pair["event"]["nodes"]]
    ids = {e["id"] for e in pair["event"]["links"]}
    for row in result["records"]:
        for path in row["explanation_paths"]:
            assert set(path["edge_ids"]) <= ids
    assert pair["graph_delta_log"]


def test_no_event_delta_zero():
    city = toy_city()
    s = toy_scenario(closed=())
    weights = {t: 1 for t in RELATION_DEFINITIONS}
    pair = paired_projection(city, s, Router().compare(city, s), digest(weights))
    assert all(x["delta_attention"] == 0 for x in compare(pair, ["bc"], weights)["records"])


def test_projection_rejects_physical_facts_from_another_scenario():
    city = toy_city()
    closed = toy_scenario()
    open_scenario = toy_scenario(closed=())
    stale = Router().compare(city, closed)
    assert stale["restrictions"] == ["bc"]
    assert open_scenario.restrictions == ()
    with pytest.raises(ValueError, match="Physical facts restrictions"):
        paired_projection(city, open_scenario, stale, digest({}))


def test_projection_rejects_stale_routes_after_seed_change():
    from urbanimpact.contracts import Scenario

    city = toy_city()
    original = toy_scenario()
    changed = Scenario.model_validate(
        {**original.model_dump(mode="json"), "seed_spec": {"entity_ids": ["ad"]}}
    )
    stale = Router().compare(city, original)
    assert stale["origins"] == ["B"]
    assert Router().compare(city, changed)["origins"] == ["A"]
    with pytest.raises(ValueError, match="Physical facts physical_context_hash"):
        paired_projection(city, changed, stale, digest({}))


def test_projection_reuses_physical_facts_for_policy_only_ablation():
    from urbanimpact.contracts import Scenario
    from urbanimpact.network import physical_context_hash

    city = toy_city()
    original = toy_scenario()
    policy_only = Scenario.model_validate(
        {
            **original.model_dump(mode="json"),
            "scenario_id": "toy-road-policy",
            "ranking": "A1",
            "objective": "transit_association",
        }
    )
    facts = Router().compare(city, original)
    assert physical_context_hash(city, original) == physical_context_hash(city, policy_only)
    paired_projection(city, policy_only, facts, digest({}))


@pytest.mark.parametrize(
    ("field", "wrong"),
    [
        ("network_hash", "0" * 64),
        ("analysis_at", "2025-01-01T00:00:00+00:00"),
        ("vehicle_class", "bus"),
        ("restrictions", []),
    ],
)
def test_projection_rejects_unbound_physical_fact_context(field, wrong):
    city = toy_city()
    scenario = toy_scenario()
    facts = Router().compare(city, scenario)
    facts[field] = wrong
    with pytest.raises(ValueError, match=f"Physical facts {field}"):
        paired_projection(city, scenario, facts, digest({}))


def test_policy_multi_type_and_single_type_invariance(pair):
    g = pair["baseline"]
    a = {t: 1 for t in RELATION_DEFINITIONS}
    b = {**a, "SEGMENT_ACCESS_TO_FACILITY": 0}
    assert not np.allclose(transition(g, a).toarray(), transition(g, b).toarray())
    g = copy.deepcopy(g)
    g["links"] = [e for e in g["links"] if e["relation_type"] == "SEGMENT_ACCESS_TO_FACILITY"]
    assert np.array_equal(transition(g, a).toarray(), transition(g, b).toarray())


def test_solver_rejects_bad_inputs_and_nonconvergence():
    assert ppr(sparse.csr_matrix((1, 1)), [1])["scores"][0] == 1
    for seed in ([0], [float("nan")], [-1]):
        with pytest.raises(ValueError):
            ppr(sparse.csr_matrix((1, 1)), seed)
    with pytest.raises(ValueError):
        ppr(sparse.csr_matrix([[0, 1], [1, 0]]), [1, 0], max_iter=1)
    with pytest.raises(ValueError):
        ppr(sparse.csr_matrix([[0.4]]), [1])


def test_projection_cannot_admit_audit_objects(pair):
    spec = copy.deepcopy(pair["baseline"]["spec"])
    spec["allowed_object_types"].append("SimulationRun")
    with pytest.raises(ValueError, match="audit"):
        project(city_objects(toy_city()), [], ProjectionSpec.model_validate(spec))


def test_static_transit_alignment_is_not_a_simulated_operational_route():
    from urbanimpact.contracts import CityPack

    data = toy_city().model_dump(mode="json")
    data["transit"] = {
        "routes": [
            {
                "id": "route-1",
                "source_id": data["sources"][0]["id"],
                "match_status": "verified",
                "edge_ids": ["bc"],
            }
        ]
    }
    city = CityPack.model_validate(data)
    scenario = toy_scenario()
    weights = {t: 1.0 for t in RELATION_DEFINITIONS}
    pair = paired_projection(city, scenario, Router().compare(city, scenario), digest(weights))
    for side in ("baseline", "event"):
        assert not any("ROUTE" in e["relation_type"] for e in pair[side]["links"])
    dependencies = pair["dependency_evidence"]
    assert dependencies["spec"]["projection_kind"] == "dependency_evidence"
    assert {e["relation_type"] for e in dependencies["links"]} == {
        "ROUTE_USES_SEGMENT",
        "SEGMENT_USED_BY_ROUTE",
    }
    assert all("bc" in (e["src"], e["dst"]) for e in dependencies["links"])
