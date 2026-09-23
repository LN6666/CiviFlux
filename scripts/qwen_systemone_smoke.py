#!/usr/bin/env python3
"""One-request smoke against a deployer-local Qwen System-One server.

Reference backend: kshetrajna12/reflex serving Qwen3.5-4B. The script never starts
or downloads a model and never sends city data. By default it refuses non-loopback
endpoints. It validates typed probabilities and records reproducibility metadata.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from verification.system_one_contract import build_request,parse_scores,validate_local_endpoint,validate_runtime_budget


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base-url',default=os.environ.get('URBANIMPACT_SYSTEM_ONE_BASE_URL','http://127.0.0.1:8008'))
    ap.add_argument('--allow-remote',action='store_true')
    ap.add_argument('--model-id',default=os.environ.get('URBANIMPACT_SYSTEM_ONE_MODEL','Qwen/Qwen3.5-4B'))
    ap.add_argument('--reflex-revision',default=os.environ.get('URBANIMPACT_REFLEX_REVISION','UNPINNED'))
    ap.add_argument('--max-questions',type=int,default=24)
    ap.add_argument('--max-wall-ms',type=int,default=5000)
    ap.add_argument('--output',type=Path,default=ROOT/'evidence'/'qwen_systemone_protocol_smoke_local.json')
    args=ap.parse_args()
    try:
        endpoint=validate_local_endpoint(args.base_url,allow_remote=args.allow_remote)
        validate_runtime_budget(max_questions=args.max_questions,max_wall_ms=args.max_wall_ms)
    except (ValueError,PermissionError) as e:
        print(f'BLOCKED_ENVIRONMENT: {e}'); return 2
    req=build_request({
        'ACCESS_FOR':'A road segment is on a verified access path to a facility.',
        'ADMIN_METADATA':'An entity appears in the same administrative file.'},
        'Retrieve evidence relevant to facility access following a road restriction.')
    payload=json.dumps(req,allow_nan=False).encode('utf-8')
    request=urllib.request.Request(endpoint,data=payload,headers={'Content-Type':'application/json'},method='POST')
    started=time.perf_counter()
    try:
        with urllib.request.urlopen(request,timeout=args.max_wall_ms/1000) as stream:
            raw=stream.read(262145)
        wall_ms=round((time.perf_counter()-started)*1000,3)
        if len(raw)>262144: raise ValueError('response exceeds cap')
        response=json.loads(raw)
        scores=parse_scores(response,set(req['questions']))
    except (urllib.error.URLError,TimeoutError,ConnectionError) as e:
        print(f'BLOCKED_ENVIRONMENT: local System-One server unavailable ({type(e).__name__})'); return 2
    except Exception as e:
        print(f'LOCAL_MODEL_FAILED: {type(e).__name__}'); return 3
    record={
      'scope':'local protocol smoke ONLY, not Helsinki graph integration',
      'provider_mode':'local_qwen',
      'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'backend':'reflex-compatible-system-one',
      'model_id':args.model_id,
      'reflex_revision':args.reflex_revision,
      'endpoint_host':urllib.parse.urlparse(args.base_url).hostname,
      'scores':scores,'questions':len(req['questions']),'wall_ms':wall_ms,
      'request_sha256':hashlib.sha256(payload).hexdigest(),
      'response_sha256':hashlib.sha256(raw).hexdigest(),
      'response_model':response.get('model'),
      'response_usage':response.get('usage'),
      'external_ai_egress': False if urllib.parse.urlparse(args.base_url).hostname in {'127.0.0.1','localhost','::1'} else True,
      'product_gate_complete':False,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    tmp=args.output.with_suffix(args.output.suffix+'.tmp');tmp.write_text(json.dumps(record,indent=2),encoding='utf-8');tmp.replace(args.output)
    print(f'Local Qwen System-One protocol smoke PASS. Full graph gate NOT satisfied. Metadata: {args.output}')
    return 0
if __name__=='__main__': raise SystemExit(main())
