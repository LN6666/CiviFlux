from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
import zipfile
from pathlib import Path
from threading import Event
import pytest
from fastapi.testclient import TestClient
from api.app import create_app
from urbanimpact.fixtures import toy_city,toy_scenario
from urbanimpact.actions import ActionError
from urbanimpact.util import digest

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path,[toy_city()])) as c:
        c.headers['Authorization']='Bearer '+c.get('/api/v1/session').json()['token']
        yield c

def create(c,ranking='A2',sid='api-case'):
    s=toy_scenario(ranking=ranking).model_dump(mode='json');s['scenario_id']=sid
    assert c.post('/api/v1/scenarios/validate',json=s).json()['valid']
    r=c.post('/api/v1/actions',json={'action_id':'create-'+sid,'action_type':'CreateScenario','scenario_id':sid,'parameters':{'scenario':s}})
    assert r.status_code==201,r.text
    return s

def run(c,s,key='unique'):
    r=c.post('/api/v1/runs',json={'citypack_id':s['citypack_id'],'scenario_id':s['scenario_id']},headers={'Idempotency-Key':key})
    assert r.status_code==202,r.text
    rid=r.json()['run_id'];c.app.state.service.futures[rid].result(timeout=10)
    return rid

def test_action_run_object_export_end_to_end(client):
    s=create(client);rid=run(client,s)
    assert client.get('/api/v1/runs/'+rid).json()['status']=='completed'
    result=client.get('/api/v1/runs/'+rid+'/results').json()
    assert result['facts']['od'][0]['baseline']['travel_time_s']==2
    assert result['facts']['od'][0]['event']['travel_time_s'] is None
    assert result['attention']['convergence']
    view=client.get('/api/v1/objects/hospital',params={'citypack_id':s['citypack_id'],'scenario_id':s['scenario_id'],'run_id':rid}).json()
    assert view['facts']==result['facts']['od']
    assert view['history'][0]['record']['status']=='committed'
    exported=client.get('/api/v1/runs/'+rid+'/export')
    assert exported.status_code==200
    with zipfile.ZipFile(BytesIO(exported.content)) as z:
        assert {'scenario.json','ontology.json','actions.json','result.json','export_manifest.json'}<=set(z.namelist())
        for name in z.namelist():
            assert client.app.state.token.encode() not in z.read(name)
    assert run(client,s)==rid

def test_failed_model_is_not_fake_pass(client):
    s=create(client,'A3');rid=run(client,s)
    state=client.get('/api/v1/runs/'+rid).json()
    assert state['status']=='failed' and state['error']['code']=='BLOCKED_API_SETUP'
    assert client.get('/api/v1/runs/'+rid+'/results').status_code==409


def test_a4_direct_control_uses_test_policy_without_ppr_or_paid_egress(tmp_path):
    class FixedTestPolicy:
        def score_relations(self, objective, definitions):
            assert objective == 'facility_access'
            return {'provider_mode': 'mock_test', 'scores': {name: 0.5 for name in definitions}}

    with TestClient(create_app(tmp_path, [toy_city()], policy_backend=FixedTestPolicy())) as api:
        api.headers['Authorization'] = 'Bearer ' + api.get('/api/v1/session').json()['token']
        scenario = create(api, 'A4', 'a4-offline-control')
        run_id = run(api, scenario)
        result = api.get('/api/v1/runs/' + run_id + '/results').json()
        assert result['provider_mode'] == 'mock_test'
        assert result['attention']['kind'] == 'direct_relation_relevance_not_risk'
        assert result['attention']['candidate_ids'] == ['hospital']
        assert len(result['attention']['records']) == 1
        assert result['attention']['convergence'] is None
        assert result['facts']['od'][0]['event']['status'] == 'unreachable'
        assert api.get('/api/v1/runs/' + run_id + '/export').status_code == 200

def test_auth_origin_host_and_no_arbitrary_crud(client):
    assert client.get('/api/v1/citypacks',headers={'Authorization':'bad'}).status_code==401
    assert client.get('/api/v1/session',headers={'Origin':'https://evil.example'}).status_code==403
    assert client.get('/api/v1/session',headers={'Sec-Fetch-Site':'cross-site'}).status_code==403
    assert client.get('/api/v1/session',headers={'Host':'evil.example'}).status_code==400
    assert client.post('/api/v1/edit_relation',json={}).status_code==404
    assert client.post('/api/v1/citypacks/import',json={'url':'http://127.0.0.1/secrets','path':'../../.env'}).status_code==422
    assert client.get('/api/v1/runs/unknown/export').status_code==404

def test_idempotency_and_job_isolation(client):
    s=create(client);rid=run(client,s)
    t=create(client,sid='other');r=client.post('/api/v1/runs',json={'citypack_id':t['citypack_id'],'scenario_id':t['scenario_id']},headers={'Idempotency-Key':'unique'})
    assert r.status_code==409
    other=run(client,t,'other-key');assert other!=rid
    assert client.get('/api/v1/runs/'+other+'/results').json()['scenario_id']=='other'

def test_cancel_is_durable(client):
    s=create(client);started=Event();release=Event();original=client.app.state.service.analysis.run
    def blocked(*a,**kw):
        started.set();release.wait(3)
        return original(*a,**kw)
    client.app.state.service.analysis.run=blocked
    r=client.post('/api/v1/runs',json={'citypack_id':s['citypack_id'],'scenario_id':s['scenario_id']});rid=r.json()['run_id']
    assert started.wait(2)
    assert client.post('/api/v1/runs/'+rid+'/cancel').status_code==200
    release.set();client.app.state.service.futures[rid].result(timeout=5)
    assert client.get('/api/v1/runs/'+rid).json()['status']=='cancelled'

def test_concurrent_stale_actions_only_one_commit(client):
    s=create(client);service=client.app.state.service;workspace=service.workspace(s['citypack_id']);before=digest(workspace.scenario(s['scenario_id']))
    from urbanimpact.contracts import ActionRequest
    requests=[ActionRequest(action_id='change'+str(i),action_type='ChangeAnalysisPolicy',scenario_id=s['scenario_id'],parameters={'ranking':'A1' if i==0 else 'A0','objective':'facility_access'},expected_overlay_hash=before) for i in range(2)]
    def apply(a):
        try:workspace.commit(a);return True
        except ActionError:return False
    with ThreadPoolExecutor(2) as pool:assert sum(pool.map(apply,requests))==1
