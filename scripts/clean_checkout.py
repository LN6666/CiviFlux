"""Verify committed HEAD from an offline export and an isolated wheel installation.

No data/model download, hosted inference or Docker is used. Missing offline cache
is BLOCKED_ENVIRONMENT, never a skipped PASS. All temporary inputs are removed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile


class CheckFailure(Exception):
    def __init__(self, stage: str, status: str, detail: str):
        self.stage, self.status, self.detail = stage, status, detail
        super().__init__(detail)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def environment() -> dict[str, str]:
    # Do not expose inherited model credentials or accidentally reuse another venv.
    allowed = ("PATH", "HOME", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL", "UV_CACHE_DIR", "SYSTEMROOT")
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env.update(
        UV_OFFLINE="true",
        UV_PYTHON_DOWNLOADS="never",
        UV_LINK_MODE="copy",
        UV_NO_PROGRESS="true",
        NO_COLOR="1",
    )
    return env


def failure_status(stage: str, output: str) -> str:
    unavailable = (
        "network connectivity is disabled",
        "when the network is disabled",
        "not found in the cache",
        "not found in cache",
        "not available in the cache",
        "no interpreter found",
        "no python interpreter",
        "no space left on device",
    )
    if stage in ("offline_sync", "wheel_build", "wheel_install") and any(
        text in output.lower() for text in unavailable
    ):
        return "BLOCKED_ENVIRONMENT"
    return "FAIL"


def command(
    stage: str,
    args: list[str],
    cwd: Path,
    env: dict[str, str],
    checks: list,
    timeout: int,
    temp: Path | None = None,
) -> str:
    started = time.monotonic()
    display = [value.replace(str(temp), "<TEMP>") if temp else value for value in args]
    record = {"stage": stage, "command": display}
    checks.append(record)
    process = subprocess.Popen(
        args,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=os.name == "posix",
    )
    try:
        output, _ = process.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        output, _ = process.communicate()
        record.update(
            status="BLOCKED_ENVIRONMENT",
            returncode=process.returncode,
            elapsed_s=round(time.monotonic() - started, 3),
            output=output[-20000:],
        )
        reason = (
            "Command exceeded its wallclock bound"
            if isinstance(error, subprocess.TimeoutExpired)
            else "Interrupted"
        )
        raise CheckFailure(stage, "BLOCKED_ENVIRONMENT", reason) from error
    record.update(
        returncode=process.returncode,
        elapsed_s=round(time.monotonic() - started, 3),
        output=output[-20000:].replace(str(temp), "<TEMP>") if temp else output[-20000:],
    )
    record["status"] = "PASS" if process.returncode == 0 else failure_status(stage, output)
    if process.returncode:
        raise CheckFailure(stage, record["status"], "Command failed; inspect recorded stage output")
    return output.strip()


SOURCE_IMPORT = """
import api.app, adapters.sumo, ontology.registry
from urbanimpact.contracts import MANIFEST
ontology.registry.validate_registry()
assert MANIFEST['ontology_version'] == '1.0.0'
print('product imports and ontology registry PASS')
"""

WHEEL_SMOKE = """
import json, sys
from importlib.resources import files
from pathlib import Path
import api.app, adapters.sumo, urbanimpact, ontology
from urbanimpact.contracts import MANIFEST, MANIFEST_PATH
from urbanimpact.fixtures import toy_city, toy_scenario
from urbanimpact.network import Router
from urbanimpact.graph import paired_projection
from urbanimpact.ranking import RELATION_DEFINITIONS, compare
from urbanimpact.util import digest
from ontology.registry import validate_registry
validate_registry()
assert files('ontology').joinpath('manifest.yaml').is_file()
assert Path(MANIFEST_PATH).is_relative_to(Path(sys.prefix)), MANIFEST_PATH
for module in (api.app, adapters.sumo, urbanimpact, ontology):
    assert Path(module.__file__).is_relative_to(Path(sys.prefix)), module.__file__
city, scenario = toy_city(), toy_scenario()
facts = Router().compare(city, scenario, origins=['A'])
policy = {key: 1.0 for key in RELATION_DEFINITIONS}
pair = paired_projection(city, scenario, facts, digest(policy))
attention = compare(pair, scenario.seed_spec.entity_ids, policy)
assert attention['convergence'] and facts['od']
assert all(entry['baseline']['status'] == 'available' for entry in facts['od'])
print(json.dumps({'ontology_version': MANIFEST['ontology_version'],
                  'packaged_manifest': True, 'isolated_imports': True,
                  'routing': True, 'ppr_converged': attention['convergence']}))
"""


def verify(repo: Path, timeout: int, report: dict) -> None:
    if not shutil.which("git") or not shutil.which("uv"):
        raise CheckFailure("prerequisites", "BLOCKED_ENVIRONMENT", "git and uv must be installed locally")
    env, checks = environment(), report["checks"]
    report["commit"] = command("committed_head", ["git", "rev-parse", "HEAD"], repo, env, checks, timeout)
    report["uv_version"] = command("uv_version", ["uv", "--version"], repo, env, checks, timeout)
    report["working_tree"] = command(
        "working_tree", ["git", "status", "--porcelain"], repo, env, checks, timeout
    )
    with tempfile.TemporaryDirectory(prefix="civiflux-clean-") as directory:
        temp = Path(directory).resolve()
        report["temporary_directory_removed"] = False
        checkout = temp / "checkout"
        checkout.mkdir()
        try:
            archive = temp / "head.tar"
            command(
                "export_head",
                ["git", "archive", "--format=tar", "--output", str(archive), report["commit"]],
                repo,
                env,
                checks,
                timeout,
                temp,
            )
            report["archive_sha256"] = sha256(archive)
            with tarfile.open(archive) as content:
                content.extractall(checkout, filter="data")
            for relative in (
                "uv.lock",
                "pyproject.toml",
                "ontology/manifest.yaml",
                "scripts/demo_product.py",
            ):
                if not (checkout / relative).is_file():
                    raise CheckFailure(
                        "export_head", "FAIL", f"Required committed file is missing: {relative}"
                    )
            report["input_hashes"] = {name: sha256(checkout / name) for name in ("uv.lock", "pyproject.toml")}
            env["UV_PROJECT_ENVIRONMENT"] = str(checkout / ".venv")
            command(
                "offline_sync",
                ["uv", "sync", "--frozen", "--offline", "--python", "3.12", "--no-python-downloads"],
                checkout,
                env,
                checks,
                timeout,
                temp,
            )
            python = checkout / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            source_env = {**env, "PYTHONPATH": f"{checkout / 'core'}{os.pathsep}{checkout}"}
            command(
                "source_import",
                [str(python), "-c", SOURCE_IMPORT],
                checkout,
                source_env,
                checks,
                timeout,
                temp,
            )
            summary = temp / "toy_summary.json"
            command(
                "toy_product_demo",
                [str(python), "scripts/demo_product.py", "--out", str(summary)],
                checkout,
                source_env,
                checks,
                timeout,
                temp,
            )
            demo = json.loads(summary.read_text())
            result_path = Path(demo["result_path"])
            result = json.loads(
                (result_path if result_path.is_absolute() else checkout / result_path).read_text()
            )
            if (
                demo["status"] != "PASS"
                or not result["attention"]["convergence"]
                or not result["facts"]["od"]
                or result["provider_mode"] != "rules"
                or result["simulation_status"] != "not_requested"
            ):
                raise CheckFailure(
                    "toy_product_demo", "FAIL", "Toy product routing/PPR result failed validation"
                )
            report["toy_demo"] = {
                "status": "PASS",
                "summary_sha256": sha256(summary),
                "od_count": len(result["facts"]["od"]),
                "ppr_converged": True,
                "provider_mode": result["provider_mode"],
            }
            command(
                "wheel_build",
                [
                    "uv",
                    "build",
                    "--wheel",
                    "--offline",
                    "--python",
                    str(python),
                    "--no-python-downloads",
                    "--out-dir",
                    str(temp / "dist"),
                ],
                checkout,
                env,
                checks,
                timeout,
                temp,
            )
            wheels = list((temp / "dist").glob("*.whl"))
            if len(wheels) != 1:
                raise CheckFailure("wheel_build", "FAIL", "Expected exactly one built wheel")
            wheel = wheels[0]
            with ZipFile(wheel) as content:
                if "ontology/manifest.yaml" not in content.namelist():
                    raise CheckFailure("wheel_contents", "FAIL", "Wheel omits ontology/manifest.yaml")
            report["wheel"] = {
                "filename": wheel.name,
                "sha256": sha256(wheel),
                "ontology_manifest_included": True,
            }
            command(
                "wheel_install",
                [
                    "uv",
                    "pip",
                    "install",
                    "--offline",
                    "--no-deps",
                    "--reinstall",
                    "--python",
                    str(python),
                    str(wheel),
                ],
                checkout,
                env,
                checks,
                timeout,
                temp,
            )
            isolated = temp / "outside_checkout"
            isolated.mkdir()
            smoke = command(
                "isolated_wheel_smoke",
                [str(python), "-I", "-c", WHEEL_SMOKE],
                isolated,
                env,
                checks,
                timeout,
                temp,
            )
            report["wheel_smoke"] = json.loads(smoke)
            if report["input_hashes"] != {name: sha256(checkout / name) for name in report["input_hashes"]}:
                raise CheckFailure(
                    "frozen_inputs", "FAIL", "Frozen installation modified lock/project inputs"
                )
        finally:
            # TemporaryDirectory performs removal even if a command or assertion fails.
            report["_temporary_directory"] = str(temp)
    report["temporary_directory_removed"] = not temp.exists()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, default=Path("evidence/wp7/clean_checkout.json"))
    parser.add_argument("--timeout", type=int, default=180, help="Maximum seconds per child command")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 600:
        parser.error("--timeout must be between 1 and 600 seconds")
    report = {
        "status": "FAIL",
        "scope": "committed HEAD offline Python installation, toy routing/PPR and wheel resources",
        "created_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "network": "disabled for uv; no data/model calls",
        "checks": [],
    }
    try:
        verify(args.repo.resolve(), args.timeout, report)
        report["status"] = "PASS"
    except CheckFailure as error:
        report.update(status=error.status, failed_stage=error.stage, detail=error.detail)
    except Exception as error:  # noqa: BLE001 - persist unexpected verification failures as FAIL evidence.
        report.update(status="FAIL", failed_stage="verification", detail=f"{type(error).__name__}: {error}")
    finally:
        temporary = report.pop("_temporary_directory", None)
        if temporary:
            report["temporary_directory_removed"] = not Path(temporary).exists()
        report["exit_code"] = {"PASS": 0, "FAIL": 1, "BLOCKED_ENVIRONMENT": 2}[report["status"]]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": report["status"],
                "commit": report.get("commit"),
                "evidence": str(args.out.resolve()),
                "exit_code": report["exit_code"],
            }
        )
    )
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
