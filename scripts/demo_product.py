"""Produce actual product artifacts through the application service, never reference oracles."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
from api.services import RunService
from urbanimpact.fixtures import toy_city,toy_scenario
from urbanimpact.contracts import ActionRequest,CityPack,Scenario
from urbanimpact.util import atomic_json,file_hash

def main():
    p=argparse.ArgumentParser();p.add_argument('--citypack');p.add_argument('--scenario');p.add_argument('--kind',choices=['road','fire'],default='road');p.add_argument('--out',default='evidence/wp0/walking_skeleton.json');a=p.parse_args()
    city=CityPack.model_validate_json(Path(a.citypack).read_bytes()) if a.citypack else toy_city()
    scenario=Scenario.model_validate_json(Path(a.scenario).read_bytes()) if a.scenario else toy_scenario(kind=a.kind)
    root=Path('.runtime/demo')/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    service=RunService(root,[city])
    try:
        service.action(ActionRequest(action_id='create',action_type='CreateScenario',scenario_id=scenario.scenario_id,parameters={'scenario':scenario.model_dump(mode='json')}))
        job=service.submit(city.citypack_id,scenario.scenario_id)
        service.futures[job['run_id']].result(timeout=120)
        state=service.state(job['run_id'])
        if state['status']!='completed':raise RuntimeError(state)
        result=service.result(job['run_id']);zip_path=service.export(job['run_id'])
        summary={'status':'PASS','scope':'product routing/ontology/fixed PPR; no Qwen live or measured traffic claim','run':state,'result_path':str(root/'runs'/job['run_id']/'result.json'),'export_path':str(zip_path),'export_sha256':file_hash(zip_path),'network_temporality':city.network_temporality,'od':result['facts']['od'],'graph_nodes':len(result['graph']['event']['nodes']),'graph_edges':len(result['graph']['event']['links']),'rank_residual':result['attention'].get('residual_l1')}
        atomic_json(Path(a.out),summary);print(a.out,summary['status'])
    finally:service.close()
if __name__=='__main__':main()
