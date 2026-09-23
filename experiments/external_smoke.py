"""Bounded harness around unmodified third-party code; no public server or AI calls."""

from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
import socket
import sys
import time
from pathlib import Path

root = Path(sys.argv[1]).resolve()
vendor = root / "experiments/vendor/SUMO_LLM_Agent"
output = root / "evidence/wp6/runtime/external"
output.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(root / "experiments/vendor/deps"))
import sumo

sumo_home = Path(sumo.__file__).parent
sys.path.insert(0, str(sumo_home / "tools"))
sys.path.insert(0, str(vendor))
os.environ["SUMO_HOME"] = str(sumo_home)
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
os.environ.pop("OPENAI_API_KEY", None)
# No third-party destination may be contacted by this smoke. Native TraCI uses loopback.
original_connect = socket.socket.connect
attempts = []


def guarded_connect(self, address):
    if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
        attempts.append("non-loopback blocked")
        raise RuntimeError("external reproduction forbids remote connections")
    return original_connect(self, address)


socket.socket.connect = guarded_connect
os.chdir(vendor)
started = time.perf_counter()
spec = importlib.util.spec_from_file_location("external_sumo_llm_agent", vendor / "script.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with module.app.test_client() as client:
    response = client.get("/")
    http = {
        "status_code": response.status_code,
        "body_bytes": len(response.data),
        "body_sha256": hashlib.sha256(response.data).hexdigest(),
        "contains_map": b"map" in response.data.lower(),
    }
# Exercise the project's own simulation loop with its supplied network/config.
module.SUMO_BINARY = str(root / ".venv/bin/sumo")
module.simulation_duration = 10
module.simulation_speed = 0
module.sumo_simulation()
result = {
    "status": "PASS_BOUNDED_EXTERNAL_SMOKE",
    "http": http,
    "simulation_results": module.simulation_results_history,
    "duration_s": time.perf_counter() - started,
    "remote_connections_attempted": len(attempts),
    "llm_calls": 0,
    "source_modified": False,
    "scope": "unmodified Flask index via in-process test client and project sumo_simulation loop10simseconds; no public listener, UI remote tiles or LLM authoring",
    "limitations": [
        "Upstream configuration enables ignore-route-errors; this smoke does not validate all demand routes.",
        "Upstream network/demand differs from CiviFlux; no runtime or quality ranking.",
        "Natural-language scenario authoring not exercised because it requires external API.",
    ],
    "dependencies": {
        name: importlib.metadata.version(name)
        for name in ["flask", "flask-socketio", "openai-agents", "openai"]
    },
}
(output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
if response.status_code != 200 or not module.simulation_results_history:
    raise SystemExit(1)
print(json.dumps(result, indent=2))
