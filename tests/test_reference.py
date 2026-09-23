from pathlib import Path
import copy
import itertools
import json
import numpy as np
import networkx as nx
import pytest
from verification.reference import (seed_vector, transition, ppr_linear, ppr_power,
    comparable_delta, canonical_hash, active, blocked_edges, route_cost)
ROOT = Path(__file__).resolve().parents[1]
TOY = json.loads((ROOT/'cases/synthetic/toy_city.json').read_text())


def setup_graph(policy=None):
    return transition(TOY['semantic_nodes'], TOY['semantic_edges'],
                      policy or TOY['all_weights_one'], TOY['seed'])


def test_linear_power_networkx_agree():
    p,s = setup_graph()
    expected = ppr_linear(p,s)
    computed, info = ppr_power(p,s)
    g=nx.from_numpy_array(p, create_using=nx.DiGraph)
    nxr=nx.pagerank(g, alpha=0.85, personalization=dict(enumerate(s)), tol=1e-13, max_iter=1000)
    np.testing.assert_allclose(computed,expected,atol=1e-11,rtol=0)
    np.testing.assert_allclose(computed,np.array([nxr[i] for i in range(len(s))]),atol=1e-11,rtol=0)
    assert info['residual_l1'] <= 1e-12
    assert abs(computed.sum()-1)<1e-12
    assert np.all(computed>=0)

@pytest.mark.parametrize('alpha',[0.0,0.4,0.85,0.95])
def test_seeded_random_graph_oracle(alpha):
    rng=np.random.default_rng(20260923)
    for n in [1,2,8,15]:
        w=rng.random((n,n)); w[w<0.7]=0
        s=rng.random(n); s/=s.sum()
        p=np.zeros_like(w)
        for i in range(n):p[i]=w[i]/w[i].sum() if w[i].sum() else s
        r,meta=ppr_power(p,s,alpha=alpha,max_iter=3000)
        np.testing.assert_allclose(r,ppr_linear(p,s,alpha),atol=3e-11,rtol=0)


def test_dangling_and_disconnected_use_same_seed():
    p,s=transition(['a','b','isolated'],[{'src':'a','dst':'b','relation_type':'r','strength':1}],{'r':1},{'a':1})
    np.testing.assert_allclose(p[1],s);np.testing.assert_allclose(p[2],s)
    r,_=ppr_power(p,s)
    assert r[2]==0 and r[1]>0


def test_single_node_and_zero_edges():
    p,s=transition(['a'],[],{}, {'a':1})
    np.testing.assert_array_equal(ppr_linear(p,s),[1])

@pytest.mark.parametrize('seed',[{}, {'a':0},{'a':-1},{'a':float('nan')},{'x':1}])
def test_invalid_seeds_rejected(seed):
    with pytest.raises(ValueError):seed_vector(['a','b'],seed)

@pytest.mark.parametrize('alpha',[-0.1,1.0,float('nan'),True])
def test_invalid_alpha_rejected(alpha):
    p,s=setup_graph()
    with pytest.raises(ValueError):ppr_linear(p,s,alpha)

@pytest.mark.parametrize('w',[-1,float('nan'),float('inf'),True])
def test_bad_strength_rejected(w):
    edges=copy.deepcopy(TOY['semantic_edges']);edges[0]['strength']=w
    with pytest.raises(ValueError):transition(TOY['semantic_nodes'],edges,TOY['all_weights_one'],TOY['seed'])


def test_orphan_unknown_type_rejected():
    edges=copy.deepcopy(TOY['semantic_edges']);edges[0]['dst']='missing'
    with pytest.raises(ValueError):transition(TOY['semantic_nodes'],edges,TOY['all_weights_one'],TOY['seed'])
    with pytest.raises(ValueError):transition(TOY['semantic_nodes'],TOY['semantic_edges'],{},TOY['seed'])


def test_not_stochastic_rejected():
    p,s=setup_graph();p[0]*=2
    with pytest.raises(ValueError):ppr_linear(p,s)


def test_nonconvergence_raises_not_pass():
    p,s=setup_graph()
    with pytest.raises(RuntimeError):ppr_power(p,s,max_iter=1,tol=1e-15)


def test_all_types_uniform_scaling_cancels():
    p,s=setup_graph()
    p2,_=setup_graph({k:7*v for k,v in TOY['all_weights_one'].items()})
    np.testing.assert_allclose(p,p2,atol=1e-15)


def test_one_relation_type_policy_cancels():
    nodes=['a','b','c']; edges=[dict(src='a',dst='b',relation_type='x',strength=1),dict(src='a',dst='c',relation_type='x',strength=2)]
    p,s=transition(nodes,edges,{'x':1},{'a':1})
    q,_=transition(nodes,edges,{'x':0.01},{'a':1})
    np.testing.assert_allclose(p,q,atol=1e-15)


def test_multirelation_policy_changes_matrix_and_ranking():
    p,s=setup_graph();q,_=setup_graph(TOY['test_policy_not_system_one_local'])
    assert not np.allclose(p,q)
    assert np.linalg.norm(ppr_linear(p,s)-ppr_linear(q,s),1)>0.05
    # A deterministic mocked policy proves code path wiring, NOT real local Qwen System-One performance.


def test_duplicate_same_destination_not_new_semantic_relation_mass():
    edges=copy.deepcopy(TOY['semantic_edges']); edges.append(copy.deepcopy(edges[0]))
    p,s=setup_graph();q,_=transition(TOY['semantic_nodes'],edges,TOY['all_weights_one'],TOY['seed'])
    np.testing.assert_allclose(p,q)


def metadata():
    return dict(node_universe_hash='nodes',seed_hash='seed',policy_hash='policy',alpha=0.85,
                normalization='relation_mixture',citypack_hash='citypack')


def test_noop_delta_zero_and_sum_zero():
    p,s=setup_graph();r=ppr_linear(p,s)
    delta=comparable_delta(r,r,metadata(),metadata())
    np.testing.assert_array_equal(delta,np.zeros(len(r)))

@pytest.mark.parametrize('key',['node_universe_hash','seed_hash','policy_hash','alpha','normalization','citypack_hash'])
def test_pair_comparability_enforced(key):
    p,s=setup_graph();r=ppr_linear(p,s);a=metadata();b=metadata();b[key]='changed'
    with pytest.raises(ValueError):comparable_delta(r,r,a,b)


def test_canonical_hash_key_order_invariant():
    assert canonical_hash({'a':1,'b':2})==canonical_hash({'b':2,'a':1})
    with pytest.raises(ValueError):canonical_hash({'bad':float('nan')})

@pytest.mark.parametrize('at,expect',[
 ('2026-05-23T17:54:59Z',False),('2026-05-23T17:55:00Z',True),
 ('2026-05-23T18:54:59Z',True),('2026-05-23T18:55:00Z',False)])
def test_halfopen_timezone_window(at,expect):
    assert active('2026-05-23T20:55:00+03:00','2026-05-23T21:55:00+03:00',at)==expect


def test_naive_and_reversed_window_rejected():
    with pytest.raises(ValueError):active('2026-05-23T20:00:00','2026-05-23T21:00:00','2026-05-23T20:30:00')
    with pytest.raises(ValueError):active('2026-05-23T21:00:00Z','2026-05-23T20:00:00Z','2026-05-23T20:30:00Z')


def test_route_real_independent_expected_numbers():
    n,e=TOY['nodes'],TOY['road_edges']
    assert route_cost(n,e,'A','H')==3
    assert route_cost(n,e,'A','H',{'bc'})==7
    assert route_cost(n,e,'A','H',{'ch'}) is None
    assert route_cost(n,e,'H','A') is None
    assert route_cost(n,e,'A','A')==0


def test_fixed_cost_edge_deletion_monotonic_all_toy_subsets():
    n,e=TOY['nodes'],TOY['road_edges'];base=route_cost(n,e,'A','H')
    for mask in itertools.product([False,True], repeat=len(e)):
        blocked={edge['id'] for edge,take in zip(e,mask) if take}
        value=route_cost(n,e,'A','H',blocked)
        assert value is None or value>=base


def test_parallel_edges_only_selected_id_blocked():
    e=[dict(id='fast',src='a',dst='b',cost_s=1),dict(id='slow',src='a',dst='b',cost_s=5)]
    assert route_cost(['a','b'],e,'a','b',{'fast'})==5


def test_bad_road_inputs_rejected():
    e=copy.deepcopy(TOY['road_edges']);e[0]['cost_s']=-1
    with pytest.raises(ValueError):route_cost(TOY['nodes'],e,'A','H')
    with pytest.raises(ValueError):route_cost(TOY['nodes'],TOY['road_edges'],'A','H',{'fake'})


def test_restriction_classes_and_unknowns():
    r=[dict(edge_ids=['bc'],valid_from='2026-05-16T09:00:00+03:00',valid_to='2026-05-16T12:00:00+03:00',blocked_classes=['passenger'])]
    t='2026-05-16T10:00:00+03:00'
    assert blocked_edges(r,t,'passenger',{'bc'})=={'bc'}
    assert blocked_edges(r,t,'emergency',{'bc'})==set()
    with pytest.raises(ValueError):blocked_edges(r,t,'spaceship',{'bc'})
    with pytest.raises(ValueError):blocked_edges(r,t,'passenger',{'other'})
    r[0]['blocked_classes']=['all']
    assert blocked_edges(r,t,'emergency',{'bc'})=={'bc'}
