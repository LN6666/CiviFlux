#!/usr/bin/env python3
"""Offline handoff integrity audit. Does NOT run/validate the future plugin."""
from pathlib import Path
import json
import re
import sys
import jsonschema
import yaml
ROOT=Path(__file__).resolve().parents[1]
errors=[]
for p in ROOT.rglob('*.json'):
    try:json.loads(p.read_text())
    except Exception as e:errors.append(f'invalid JSON {p.name}: {type(e).__name__}')
for p in ROOT.rglob('*.yaml'):
    try:yaml.safe_load(p.read_text())
    except Exception as e:errors.append(f'invalid YAML {p.name}: {type(e).__name__}')
wpdoc=json.loads((ROOT/'execution/work_packages.json').read_text())
goaldoc=json.loads((ROOT/'execution/goals.json').read_text())
wps=wpdoc['work_packages']
goals=goaldoc['goals']
if len(wps)!=8 or len(goals)!=goaldoc.get('goal_count'):errors.append('work package/goal count mismatch')
if len({g['id'] for g in goals})!=len(goals):errors.append('duplicate goal IDs')
for w in wps:
    for name in w['docs']+[w['prompt']]:
        if not (ROOT/name).is_file():errors.append(f'missing WP reference {name}')
    if not all(d in {x['id'] for x in wps} for d in w['depends_on']):errors.append('unknown WP dependency')
    if set(w['goal_ids'])!={g['id'] for g in goals if g['work_package']==w['id']}:errors.append('goal index mismatch')
ids={s['id'] for s in json.loads((ROOT/'sources/registry.json').read_text())['sources']}
for p in (ROOT/'docs').glob('*.md'):
    for ref in re.findall(r'\bS\d{2}\b',p.read_text()):
        if ref not in ids:errors.append(f'unknown source {ref} in {p.name}')
for p in (ROOT/'contracts').glob('*.schema.json'):
    try:jsonschema.Draft202012Validator.check_schema(json.loads(p.read_text()))
    except Exception as e:errors.append(f'invalid schema {p.name}: {type(e).__name__}')
if (ROOT/'evidence/qwen_systemone_protocol_smoke_local.json').exists():
    print('NOTICE live smoke present; audit does not certify graph integration')
print('\n'.join(errors) if errors else f'PACK AUDIT PASS: {len(wps)} work packages, {len(goals)} goals, {len(ids)} registered sources.')
raise SystemExit(1 if errors else 0)
