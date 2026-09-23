from pathlib import Path
import copy, hashlib, importlib.util, json, subprocess, sys
import jsonschema, pytest
from verification.system_one_contract import build_request,parse_scores,validate_local_endpoint,validate_runtime_budget,factor
ROOT=Path(__file__).resolve().parents[1]
MOCK=json.loads((ROOT/'cases/synthetic/system_one_response_mock.json').read_text())


def test_system_one_request_semantics_in_instructions_not_only_key():
    req=build_request({'ACCESS_FOR':'A road is used to access a facility.','METADATA':'An admin code is shared.'},'facility access')
    assert 'model' not in req
    for key,q in req['questions'].items():
        assert key in q['instructions'] and q['type']=='score' and len(q['criteria'])==3


def test_score_is_expected_rubric_level_not_confidence():
    assert parse_scores(MOCK,{'access'})=={'access':0.875}
    assert MOCK['fixture_kind']=='MOCK_NOT_REAL_LOCAL_MODEL'

@pytest.mark.parametrize('mutation',['missing_answer','extra_answer','bad_type','bad_score','bad_probs','nan','bad_confidence','bad_legend'])
def test_bad_system_one_response_fails_closed(mutation):
    d=copy.deepcopy(MOCK);a=d['answers']['access']
    if mutation=='missing_answer':d['answers']={}
    elif mutation=='extra_answer':d['answers']['extra']=copy.deepcopy(a)
    elif mutation=='bad_type':a['type']='noul'
    elif mutation=='bad_score':a['score']=0.5
    elif mutation=='bad_probs':a['probabilities']['2']=0.2
    elif mutation=='nan':a['score']=float('nan')
    elif mutation=='bad_confidence':a['confidence']=2
    elif mutation=='bad_legend':a['legend']={}
    with pytest.raises(ValueError):parse_scores(d,{'access'})


def test_endpoint_is_local_by_default_and_remote_requires_optin():
    assert validate_local_endpoint('http://127.0.0.1:8008').endswith('/v1/systemone')
    assert validate_local_endpoint('http://localhost:8008/').endswith('/v1/systemone')
    with pytest.raises(PermissionError): validate_local_endpoint('https://gpu.example.org:8008')
    assert validate_local_endpoint('https://gpu.example.org:8008',allow_remote=True).endswith('/v1/systemone')

@pytest.mark.parametrize('args',[{'max_questions':0,'max_wall_ms':1000},{'max_questions':25,'max_wall_ms':1000},{'max_questions':2,'max_wall_ms':0}])
def test_local_runtime_budget_fails_closed(args):
    with pytest.raises(PermissionError):validate_runtime_budget(**args)


def test_local_smoke_without_server_blocks_environment_not_external_ai():
    # Use an unused high local port so the test cannot call a paid/external service.
    r=subprocess.run([sys.executable,str(ROOT/'scripts/qwen_systemone_smoke.py'),'--base-url','http://127.0.0.1:65534','--max-wall-ms','100'],cwd=ROOT,capture_output=True,text=True,timeout=5)
    assert r.returncode==2 and 'BLOCKED_ENVIRONMENT' in r.stdout
    assert not (ROOT/'evidence/qwen_systemone_protocol_smoke_local.json').exists()


def test_factor_positive_floor_and_one():
    assert factor(0)==0.1 and factor(1)==1
    with pytest.raises(ValueError):factor(1.1)


def test_schemas_are_valid_and_synthetic_scenario_passes():
    for path in (ROOT/'contracts').glob('*.schema.json'):
        jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text()))
    schema=json.loads((ROOT/'contracts/scenario.schema.json').read_text())
    case=json.loads((ROOT/'cases/synthetic/scenario_valid.json').read_text())
    jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(case)
    bad=copy.deepcopy(case);bad['kind']='fire'
    with pytest.raises(jsonschema.ValidationError):jsonschema.validate(bad,schema)
    bad=copy.deepcopy(case);bad['risk_percent']=0.92
    with pytest.raises(jsonschema.ValidationError):jsonschema.validate(bad,schema)


def gate_module():
    spec=importlib.util.spec_from_file_location('gate',ROOT/'scripts/check_release.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def test_product_currently_blocked_not_confused_with_reference_tests():
    m=gate_module();d=json.loads((ROOT/'evidence/product_release.json').read_text());errors=m.check_release(d,ROOT)
    assert len(errors)>=11 and any('GATE-QWEN-SYSTEM-ONE' in e for e in errors)


def fake_gate_doc(tmp_path):
    d=json.loads((ROOT/'evidence/product_release.json').read_text());f=tmp_path/'evidence.txt';f.write_text('Synthetic gate-check fixture, NOT proof of product completion.')
    digest=hashlib.sha256(f.read_bytes()).hexdigest();d['engineering_complete']=True
    for g in d['gates'].values():g.update(status='PASS',commit='TEST_ONLY',executed_at='2026-09-23T12:00:00Z',commands=[{'command':'synthetic_fixture','exit_code':0}],evidence_files=[{'path':'evidence.txt','sha256':digest}])
    return d


def test_structural_gate_pass_is_not_claim_of_truth(tmp_path):
    assert gate_module().check_release(fake_gate_doc(tmp_path),tmp_path)==[]


def test_gate_missing_evidence_hash_paths_and_environment_block(tmp_path):
    d=fake_gate_doc(tmp_path);g=d['gates']['GATE-QWEN-SYSTEM-ONE'];g['evidence_files'][0]['sha256']='0'*64
    assert any('hash mismatch' in s for s in gate_module().check_release(d,tmp_path))
    g['evidence_files'][0]['path']='../escape.txt';assert any('escapes' in s for s in gate_module().check_release(d,tmp_path))
    g['status']='BLOCKED_ENVIRONMENT';assert any('BLOCKED_ENVIRONMENT' in s for s in gate_module().check_release(d,tmp_path))


def test_real_evidence_not_fabricated_into_runnable_case():
    road=json.loads((ROOT/'cases/helsinki_cityrun_2026/case_evidence.json').read_text());fire=json.loads((ROOT/'cases/helsinki_fire_2026/case_evidence.json').read_text())
    assert road['case_runnable'] is False and road['facts'][0]['exact_start'] is None
    assert fire['event_date']=='2026-05-23' and fire['actual_cordon'] is None and fire['coordinates'] is None and fire['case_runnable'] is False
