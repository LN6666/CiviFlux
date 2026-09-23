"""Check release evidence structure and whether PASS evidence applies to this checkout.

Neither the manifest's exit codes nor its file hashes prove that a command ran. A
release still needs inspection of trusted CI/manual run records and gate scope.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]

# Be conservative: every PASS gate is invalidated by a change to any versioned
# product, test, data fixture, dependency, build input, or runtime case input.
# Attestation output is excluded to avoid changing the code it attests, but the
# formal boundary report is read by the API and must invalidate prior PASSes.
# Keep this list broader than an individual gate's inputs.
CONTROLLED_INPUTS = (
    ".github/workflows",
    ".dockerignore",
    ".gitignore",
    ".env.example",
    "Makefile",
    "adapters",
    "api",
    "cases",
    "comparison",
    "config",
    "contracts",
    "core",
    "data",
    "deploy",
    "evidence/wp2/helsinki_formal_boundary_case.json",
    "experiments",
    "ontology",
    "prompts",
    "pyproject.toml",
    "requirements-verification.txt",
    "scripts",
    "sources",
    "test_suite",
    "tests",
    "uv.lock",
    "verification",
    "web",
)
# A README inside a controlled directory is still documentation. The excluded
# suffix is not used by a current runtime input; if that changes, revisit this
# pathspec and add the concrete runtime file to the controlled set.
CONTROLLED_PATHS = (*CONTROLLED_INPUTS, ":(exclude,glob)**/*.md")
COMMIT_SHA = re.compile(r"[0-9a-f]{40}\Z")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def check_release(document: dict, root: Path) -> list[str]:
    errors = []
    schema = json.loads((ROOT / "contracts/release.schema.json").read_text())
    try:
        jsonschema.Draft202012Validator(schema).validate(document)
    except jsonschema.ValidationError as e:
        return [f"SCHEMA: {e.message}"]
    for name, gate in document["gates"].items():
        if gate["status"] != "PASS":
            errors.append(f"{name}: {gate['status']}")
            continue
        if not gate["commit"] or not gate["executed_at"]:
            errors.append(f"{name}: missing commit/execution time")
        if not gate["commands"] or any(c["exit_code"] != 0 for c in gate["commands"]):
            errors.append(f"{name}: missing or failed commands")
        if not gate["evidence_files"]:
            errors.append(f"{name}: no evidence files")
        for evidence in gate["evidence_files"]:
            path = (root / evidence["path"]).resolve()
            if not path.is_relative_to(root.resolve()):
                errors.append(f"{name}: evidence path escapes repository")
                continue
            if not path.is_file():
                errors.append(f"{name}: missing {evidence['path']}")
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != evidence["sha256"]:
                errors.append(f"{name}: evidence hash mismatch {evidence['path']}")
    if not document["engineering_complete"]:
        errors.append("engineering_complete is false")
    return errors


def check_current_revision(document: dict, root: Path) -> list[str]:
    """Reject stale PASS claims; leave command-content verification to CI/review.

    A gate's recorded commit may precede HEAD by documentation/evidence commits,
    but the controlled inputs must be byte-identical in Git and clean locally.
    This avoids a self-referential requirement to name the manifest's own commit.
    """
    passed = {name: gate for name, gate in document["gates"].items() if gate["status"] == "PASS"}
    if not passed:
        return []
    try:
        checkout = _git(root, "rev-parse", "--show-toplevel")
        if checkout.returncode or Path(checkout.stdout.strip()).resolve() != root.resolve():
            return ["REVISION: release root is not a Git checkout root"]
        head = _git(root, "rev-parse", "HEAD")
        if head.returncode:
            return ["REVISION: cannot determine HEAD"]
        dirty = _git(root, "status", "--porcelain=v1", "--untracked-files=all", "--", *CONTROLLED_PATHS)
        if dirty.returncode:
            return ["REVISION: cannot inspect uncommitted controlled inputs"]
        errors = []
        if dirty.stdout.strip():
            errors.append("REVISION: uncommitted or untracked controlled inputs")
        checked: dict[str, str | None] = {}
        for name, gate in passed.items():
            commit = gate["commit"]
            if not isinstance(commit, str) or not COMMIT_SHA.fullmatch(commit):
                errors.append(f"{name}: PASS commit must be a full Git SHA")
                continue
            if commit not in checked:
                exists = _git(root, "cat-file", "-e", f"{commit}^{{commit}}")
                if exists.returncode:
                    checked[commit] = "unknown Git commit"
                else:
                    ancestor = _git(root, "merge-base", "--is-ancestor", commit, head.stdout.strip())
                    if ancestor.returncode:
                        checked[commit] = "PASS commit is not an ancestor of HEAD"
                    else:
                        diff = _git(
                            root,
                            "diff",
                            "--quiet",
                            "--no-ext-diff",
                            commit,
                            head.stdout.strip(),
                            "--",
                            *CONTROLLED_PATHS,
                        )
                        if diff.returncode == 1:
                            checked[commit] = "stale PASS evidence: controlled inputs changed since commit"
                        elif diff.returncode:
                            checked[commit] = "cannot compare controlled inputs with PASS commit"
                        else:
                            checked[commit] = None
            if checked[commit]:
                errors.append(f"{name}: {checked[commit]} ({commit[:12]})")
        return errors
    except (OSError, subprocess.TimeoutExpired):
        return ["REVISION: Git inspection failed"]


if __name__ == "__main__":
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "evidence/current_product_release.json"
    try:
        document = json.loads(source.read_text())
        errors = check_release(document, ROOT)
        if not any(error.startswith("SCHEMA:") for error in errors):
            errors.extend(check_current_revision(document, ROOT))
    except (ValueError, OSError) as e:
        print(f"INVALID MANIFEST: {type(e).__name__}")
        raise SystemExit(2)
    print(
        "\n".join(errors)
        if errors
        else "STRUCTURE AND REVISION PASS; verify trusted CI content before release."
    )
    raise SystemExit(1 if errors else 0)
