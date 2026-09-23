from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def reproduce(root: Path) -> dict:
    vendor = root / "experiments/vendor/SUMO_LLM_Agent"
    out = root / "evidence/wp6"
    out.mkdir(parents=True, exist_ok=True)
    if not (vendor / ".git").exists():
        raise RuntimeError(
            "Pinned neighbor checkout missing; consult reproduction_notes. No implicit network fetch."
        )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=vendor, text=True).strip()
    if commit != "f06f6098626eb184bb3a3334b1b20639dda6b842":
        raise RuntimeError("Neighbor revision differs from reviewed pin")
    command = [sys.executable, str(root / "experiments/external_smoke.py"), str(root)]
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "TMPDIR", "SYSTEMROOT", "LANG"}}
    env["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, env=env)
        (out / "external_smoke.log").write_text(result.stdout + "\n" + result.stderr)
        artifact = root / "evidence/wp6/runtime/external/result.json"
        details = (
            json.loads(artifact.read_text())
            if result.returncode == 0 and artifact.exists()
            else {
                "status": "BLOCKED_EXTERNAL_REPRODUCTION",
                "scope": "unmodified-neighbor smoke failed; log preserved",
            }
        )
        details.update(command=command, exit_code=result.returncode)
    except subprocess.TimeoutExpired:
        details = {
            "status": "BLOCKED_EXTERNAL_REPRODUCTION",
            "command": command,
            "exit_code": 124,
            "reason": "60second wall budget exceeded",
        }
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=vendor, text=True)
    details.update(
        project="SUMO_LLM_Agent",
        repository="https://github.com/xuyimingxym/SUMO_LLM_Agent",
        commit=commit,
        license="MIT",
        source_script_sha256=hashlib.sha256((vendor / "script.py").read_bytes()).hexdigest(),
        git_status=dirty,
        checked_on="2026-09-24",
    )
    (out / "external_reproduction.json").write_text(json.dumps(details, indent=2) + "\n")
    return details
