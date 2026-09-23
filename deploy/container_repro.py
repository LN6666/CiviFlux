"""Build and exercise the pinned Linux image; emit honest machine-readable evidence.

Run from a clean checkout on an Ubuntu runner with Docker Buildx available.  The
smoke container has no network interface, model key, mounted host data, or writable
application filesystem.  A missing daemon is BLOCKED_ENVIRONMENT, never PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_PATTERN = re.compile(r"^FROM (\S+@sha256:[a-f0-9]{64})(?: AS \w+)?$", re.MULTILINE)


class CheckFailure(Exception):
    def __init__(self, stage: str, status: str, message: str):
        self.stage = stage
        self.status = status
        super().__init__(message)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def static_inputs() -> dict:
    dockerfile = (ROOT / "deploy/Dockerfile").read_text()
    bases = BASE_PATTERN.findall(dockerfile)
    if len(bases) != 2 or not bases[0].startswith("node:") or not bases[1].startswith("python:"):
        raise CheckFailure("static_inputs", "FAIL", "Both runtime and web base images need pinned OCI digests")
    if "snapshot.debian.org/archive/debian/20260920T000000Z" not in dockerfile:
        raise CheckFailure("static_inputs", "FAIL", "The Debian package index is not snapshot-pinned")
    if "uv sync --frozen --no-dev --no-editable" not in dockerfile:
        raise CheckFailure("static_inputs", "FAIL", "Runtime Python dependencies must use the frozen lock")
    ignore = (ROOT / ".dockerignore").read_text().splitlines()
    if not {".env", ".env.*", "data", "evidence", ".runtime"}.issubset(set(ignore)):
        raise CheckFailure("static_inputs", "FAIL", "Build context may contain credentials or local city data")
    paths = ("deploy/Dockerfile", "deploy/container_smoke.py", "uv.lock", "web/package-lock.json")
    return {
        "base_images": bases,
        "debian_snapshot": "20260920T000000Z",
        "input_sha256": {path: file_hash(ROOT / path) for path in paths},
    }


def command(stage: str, args: list[str], timeout: int, checks: list[dict]) -> str:
    started = time.monotonic()
    record = {"stage": stage, "command": args, "timeout_s": timeout}
    checks.append(record)
    try:
        result = subprocess.run(
            args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=timeout, check=False,
        )
    except FileNotFoundError as error:
        record.update(status="BLOCKED_ENVIRONMENT", exit_code=None, output=str(error))
        raise CheckFailure(stage, "BLOCKED_ENVIRONMENT", "Required Docker CLI is unavailable") from error
    except subprocess.TimeoutExpired as error:
        record.update(status="FAIL", exit_code=None, output=str(error))
        raise CheckFailure(stage, "FAIL", f"{stage} exceeded its {timeout}s bound") from error
    record.update(
        status="PASS" if result.returncode == 0 else "FAIL",
        exit_code=result.returncode,
        elapsed_s=round(time.monotonic() - started, 3),
        output=result.stdout[-6000:],
    )
    if result.returncode != 0:
        status = "BLOCKED_ENVIRONMENT" if stage == "docker_daemon" else "FAIL"
        record["status"] = status
        raise CheckFailure(stage, status, f"{stage} exited {result.returncode}; see recorded output")
    return result.stdout.strip()


def verify(report: dict, out: Path) -> None:
    report["inputs"] = static_inputs()
    checks = report["checks"]
    report["git_commit"] = command("git_commit", ["git", "rev-parse", "HEAD"], 15, checks)
    report["docker_server"] = command(
        "docker_daemon", ["docker", "version", "--format", "{{.Server.Version}}"], 20, checks
    )
    command("docker_buildx", ["docker", "buildx", "version"], 20, checks)
    image_tag = "civiflux-container-check:" + report["inputs"]["input_sha256"]["deploy/Dockerfile"][:12]
    metadata = out.parent / "build-metadata.json"
    command(
        "docker_build",
        [
            "docker", "buildx", "build", "--platform", "linux/amd64", "--pull", "--load",
            "--progress", "plain", "--metadata-file", str(metadata), "--tag", image_tag,
            "--file", "deploy/Dockerfile", ".",
        ],
        1200,
        checks,
    )
    build_metadata = json.loads(metadata.read_text())
    image = json.loads(
        command("image_inspect", ["docker", "image", "inspect", "--format", "{{json .}}", image_tag], 30, checks)
    )
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image["Id"]):
        raise CheckFailure("image_inspect", "FAIL", "Built image has no content-addressed image ID")
    manifest_digest = build_metadata.get("containerimage.digest")
    if manifest_digest is not None and not re.fullmatch(r"sha256:[a-f0-9]{64}", manifest_digest):
        raise CheckFailure("image_inspect", "FAIL", "Buildx returned an invalid image manifest digest")
    report["image"] = {
        "tag": image_tag,
        "id": image["Id"],
        "repo_digests": image.get("RepoDigests") or [],
        "buildx_manifest_digest": manifest_digest,
        "architecture": image["Architecture"],
        "os": image["Os"],
    }
    if (image["Os"], image["Architecture"]) != ("linux", "amd64"):
        raise CheckFailure("image_inspect", "FAIL", "Built image platform is not linux/amd64")
    output = command(
        "container_smoke",
        [
            "docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--pids-limit", "128", "--memory", "2g",
            "--tmpfs", "/workspace:rw,nosuid,nodev,size=128m",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m",
            "--env", "CIVIFLUX_TOY_ONLY=1",
            "--env", "QWEN_API_ALLOW_EGRESS=0", "--env", "QWEN_API_MAX_CALLS=0",
            "--env", "SIMPLEJEV_ALLOW_EGRESS=0", "--env", "SIMPLEJEV_MAX_CALLS=0",
            "--entrypoint", "/app/.venv/bin/python", image_tag, "/app/deploy/container_smoke.py",
        ],
        150,
        checks,
    )
    try:
        smoke = json.loads(output.splitlines()[-1])
    except (ValueError, IndexError) as error:
        raise CheckFailure("container_smoke", "FAIL", "Smoke did not return JSON evidence") from error
    if smoke.get("status") != "PASS":
        raise CheckFailure("container_smoke", "FAIL", "Smoke did not report PASS")
    report["smoke"] = smoke
    report["status"] = "PASS"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("evidence/wp7/container_reproduction.json"))
    parser.add_argument("--static-only", action="store_true", help="check pinned inputs without claiming a build")
    args = parser.parse_args()
    out = (ROOT / args.out).resolve() if not args.out.is_absolute() else args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "NOT_RUN",
        "scope": "linux/amd64 pinned-image build and offline synthetic/API/SUMO smoke",
        "checked_at": datetime.now(UTC).isoformat(),
        "checks": [],
    }
    try:
        if args.static_only:
            report["inputs"] = static_inputs()
            report["status"] = "STATIC_ONLY"
        else:
            verify(report, out)
    except CheckFailure as error:
        report.update(status=error.status, failed_stage=error.stage, error=str(error))
    except Exception as error:  # noqa: BLE001 - always write an artifact for unexpected CI failures
        report.update(status="FAIL", failed_stage="unexpected", error=str(error))
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(f"container reproducibility: {report['status']} -> {out}")
    return 0 if report["status"] in ("PASS", "STATIC_ONLY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
