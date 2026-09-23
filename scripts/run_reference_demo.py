#!/usr/bin/env python3
"""Generate actual tiny-graph reference results; no city data/API/SUMO calls."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from verification.reference import transition,ppr_power,ppr_linear,route_cost,canonical_hash
case=json.loads((ROOT/'cases/synthetic/toy_city.json').read_text())
p,s=transition(case['semantic_nodes'],case['semantic_edges'],case['all_weights_one'],case['seed'])
q,_=transition(case['semantic_nodes'],case['semantic_edges'],case['test_policy_not_system_one_local'],case['seed'])
r,info=ppr_power(p,s);r2,info2=ppr_power(q,s)
result={
 'scope':'HANDOFF_REFERENCE_ONLY','synthetic':True,'real_city_data':False,'system_one_local':False,'sumo_run':False,
 'claim':'Verifies toy routing and typed policy -> transition -> PPR wiring. Does not verify city predictions or Qwen System-One usefulness.',
 'road_oracle':{'baseline_A_to_H_s':route_cost(case['nodes'],case['road_edges'],'A','H'),
 'close_bc_A_to_H_s':route_cost(case['nodes'],case['road_edges'],'A','H',{'bc'}),
 'close_ch_A_to_H_s':route_cost(case['nodes'],case['road_edges'],'A','H',{'ch'})},
 'fixed_ppr':dict(zip(case['semantic_nodes'],map(float,r))),
 'mock_policy_ppr':dict(zip(case['semantic_nodes'],map(float,r2))),
 'policy_ablation_l1':float(np.linalg.norm(r-r2,1)),
 'not_event_delta':True,
 'fixed_numeric_checks':info,'mock_policy_numeric_checks':info2,
 'linear_oracle_max_abs_error':float(np.max(np.abs(r-ppr_linear(p,s)))),
 'fixture_hash':canonical_hash(case),
 'fixed_transition_hash':canonical_hash(p.tolist()),
 'mock_transition_hash':canonical_hash(q.tolist())}
output=ROOT/'evidence/reference_outcomes.json'
output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
