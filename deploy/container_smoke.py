"""Exercise the installed Linux image entirely inside a network-disabled container.

This is run by ``container_repro.py`` under Docker ``--network none``.  It uses
the image's production Python environment, HTTP server, and SUMO binaries;
there is no test-runner dependency or hosted model request.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

BASE_URL = "http://127.0.0.1:8765"
APP_ROOT = Path(__file__).resolve().parents[1]


def request(path: str, *, token: str | None = None, body: dict | None = None) -> dict | bytes:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, sort_keys=True).encode()
    with urllib.request.urlopen(
        urllib.request.Request(BASE_URL + path, data=data, headers=headers), timeout=5
    ) as response:
        content = response.read()
        if response.headers.get_content_type() == "application/json":
            return json.loads(content)
        return content


def check_api(workspace: Path) -> dict:
    from urbanimpact.fixtures import toy_scenario

    server_log = workspace / "server.log"
    env = {**os.environ, "CIVIFLUX_WORKSPACE": str(workspace / "app"), "CIVIFLUX_TOY_ONLY": "1"}
    with server_log.open("wb") as stream:
        server = subprocess.Popen(
            [sys.executable, "-m", "api", "--port", "8765"],
            cwd=APP_ROOT,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    raise RuntimeError("API process exited before health check")
                try:
                    health = request("/api/v1/health")
                    break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.1)
            else:
                raise TimeoutError("API did not become healthy within 20 seconds")
            if health["status"] != "ok":
                raise RuntimeError("API health status is not ok")
            token = request("/api/v1/session")["token"]
            capabilities = request("/api/v1/capabilities", token=token)
            if capabilities["qwen"]["configured"]:
                raise RuntimeError("Model must remain unconfigured in offline container smoke")
            citypacks = request("/api/v1/citypacks", token=token)
            if len(citypacks) != 1 or citypacks[0]["citypack_id"] != "TOY-DUAL-CORRIDOR":
                raise RuntimeError("Offline smoke requires exactly the synthetic citypack")
            scenario = toy_scenario(ranking="A2").model_dump(mode="json")
            scenario["scenario_id"] = "container-smoke"
            validation = request("/api/v1/scenarios/validate", token=token, body=scenario)
            if not validation["valid"]:
                raise RuntimeError("Synthetic scenario did not validate")
            request(
                "/api/v1/actions",
                token=token,
                body={
                    "action_id": "container-create",
                    "action_type": "CreateScenario",
                    "scenario_id": scenario["scenario_id"],
                    "parameters": {"scenario": scenario},
                },
            )
            run = request(
                "/api/v1/runs",
                token=token,
                body={"citypack_id": scenario["citypack_id"], "scenario_id": scenario["scenario_id"]},
            )
            run_id = run["run_id"]
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                state = request("/api/v1/runs/" + run_id, token=token)
                if state["status"] in ("completed", "failed", "cancelled"):
                    break
                time.sleep(0.1)
            else:
                raise TimeoutError("Synthetic API run did not finish within 30 seconds")
            if state["status"] != "completed":
                raise RuntimeError(f"Synthetic API run ended as {state['status']}: {state.get('error')}")
            result = request("/api/v1/runs/" + run_id + "/results", token=token)
            facts = result["facts"]["od"]
            if not facts or not result["attention"]["convergence"]:
                raise RuntimeError("Installed routing or PageRank result is incomplete")
            archive = request("/api/v1/runs/" + run_id + "/export", token=token)
            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                if not {"scenario.json", "ontology.json", "actions.json", "result.json"}.issubset(
                    bundle.namelist()
                ):
                    raise RuntimeError("Export omits required replay contents")
                if any(token.encode() in bundle.read(name) for name in bundle.namelist()):
                    raise RuntimeError("Export includes the local session token")
            return {
                "health": health,
                "qwen_status": capabilities["qwen"]["status"],
                "citypack_id": citypacks[0]["citypack_id"],
                "scenario_status": state["status"],
                "od_count": len(facts),
                "ppr_converged": result["attention"]["convergence"],
                "export_sha256": hashlib.sha256(archive).hexdigest(),
            }
        except BaseException as error:
            raise RuntimeError(f"{error}; server log tail: {server_log.read_text(errors='replace')[-2000:]}") from error
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


def check_sumo(workspace: Path) -> dict:
    from adapters.sumo import Demand, Limits, SumoAdapter
    from adapters.sumo.fixtures import dual_corridor

    city, scenario = dual_corridor()
    adapter = SumoAdapter()
    folder = workspace / "sumo"
    linker = {}
    if sys.platform.startswith("linux") and shutil.which("ldd"):
        import sumo as sumo_package

        for name in ("sumo", "netconvert"):
            native = Path(sumo_package.SUMO_HOME) / "bin" / name
            result = subprocess.run(
                ["ldd", str(native)], capture_output=True, text=True, timeout=10, check=False
            )
            output = result.stdout + result.stderr
            missing = sorted(set(re.findall(r"\b(\S+)\s+=>\s+not found", output)))
            linker[name] = {
                "native_binary": str(native),
                "exit_code": result.returncode,
                "missing_libraries": missing,
                "output_tail": output[-6000:],
            }
        if any(item["missing_libraries"] for item in linker.values()):
            raise RuntimeError(f"SUMO native binary has missing libraries: {json.dumps(linker, sort_keys=True)}")
    try:
        pair = adapter.run_pair(
            city,
            scenario,
            (Demand("synthetic-v0", ("sa", "ab", "bc", "ch")),),
            folder,
            Limits(duration_s=120, wallclock_s=30, max_vehicles=4, max_output_bytes=20_000_000),
        )
    except BaseException as error:
        # The temporary workspace is deleted after this function returns, so put
        # the bounded native log and linker evidence into the CI JSON artifact.
        diagnostic = {
            "logs": {
                path.name: path.read_text(errors="replace")[-2500:]
                for path in sorted(folder.glob("*.log"))
            },
            "entrypoints": {"sumo": adapter.sumo, "netconvert": adapter.netconvert},
            "native_linker": linker,
        }
        raise RuntimeError(f"SUMO pair failed: {error}; diagnostic={json.dumps(diagnostic, sort_keys=True)}") from error
    if pair["status"] != "PASS" or pair["engine"] != "real_local_sumo":
        raise RuntimeError("Actual SUMO pair did not pass")
    return {
        "engine": pair["engine"],
        "version": pair["sumo_version"],
        "demand_kind": pair["demand_kind"],
        "baseline_arrived": pair["baseline"]["arrived"],
        "event_arrived": pair["event"]["arrived"],
        "network_sha256": pair["network_sha256"],
        "native_linker_missing_libraries": {
            name: item["missing_libraries"] for name, item in linker.items()
        },
    }


def main() -> int:
    required_flags = (
        "QWEN_API_ALLOW_EGRESS",
        "QWEN_API_MAX_CALLS",
        "SIMPLEJEV_ALLOW_EGRESS",
        "SIMPLEJEV_MAX_CALLS",
    )
    if any(os.environ.get(name) != "0" for name in required_flags):
        raise RuntimeError("All model egress and call limits must be zero")
    if any(os.environ.get(name) for name in ("FEATHERLESS_API_KEY", "DASHSCOPE_API_KEY")):
        raise RuntimeError("Container smoke must not receive model credentials")
    if not (APP_ROOT / "web/dist/index.html").is_file():
        raise RuntimeError("Built web bundle is missing from the runtime image")
    with tempfile.TemporaryDirectory(prefix="smoke-", dir="/workspace") as directory:
        workspace = Path(directory)
        report = {
            "status": "PASS",
            "scope": "Linux installed image; synthetic city, actual local SUMO, API HTTP and export; no hosted model or measured-city claim",
            "model_egress": "disabled_by_environment_and_docker_network_none",
            "python": sys.version.split()[0],
            "web_bundle": True,
            "api": check_api(workspace),
            "sumo": check_sumo(workspace),
        }
        print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(1) from error
