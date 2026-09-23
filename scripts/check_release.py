#!/usr/bin/env python3
"""Structural and artifact-integrity gate, NOT proof that evidence is truthful."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def check_release(document: dict, root: Path) -> list[str]:
    errors = []
    schema = json.loads((ROOT/'contracts/release.schema.json').read_text())
    try:
        jsonschema.Draft202012Validator(schema).validate(document)
    except jsonschema.ValidationError as e:
        return [f'SCHEMA: {e.message}']
    for name, gate in document['gates'].items():
        if gate['status'] != 'PASS':
            errors.append(f'{name}: {gate["status"]}')
            continue
        if not gate['commit'] or not gate['executed_at']:
            errors.append(f'{name}: missing commit/execution time')
        if not gate['commands'] or any(c['exit_code'] != 0 for c in gate['commands']):
            errors.append(f'{name}: missing or failed commands')
        if not gate['evidence_files']:
            errors.append(f'{name}: no evidence files')
        for evidence in gate['evidence_files']:
            path = (root/evidence['path']).resolve()
            if not path.is_relative_to(root.resolve()):
                errors.append(f'{name}: evidence path escapes repository'); continue
            if not path.is_file():
                errors.append(f'{name}: missing {evidence["path"]}'); continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != evidence['sha256']:
                errors.append(f'{name}: evidence hash mismatch {evidence["path"]}')
    if not document['engineering_complete']:
        errors.append('engineering_complete is false')
    return errors

if __name__ == '__main__':
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT/'evidence/current_product_release.json'
    try:
        errors = check_release(json.loads(source.read_text()), ROOT)
    except (ValueError, OSError) as e:
        print(f'INVALID MANIFEST: {type(e).__name__}'); raise SystemExit(2)
    print('\n'.join(errors) if errors else 'STRUCTURAL GATE PASS; inspect actual CI content before release.')
    raise SystemExit(1 if errors else 0)
