"""A PASS record may be reused only while its versioned inputs are unchanged."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from scripts.check_release import check_current_revision, check_release

ROOT = Path(__file__).resolve().parents[2]


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def commit(repo: Path, message: str) -> str:
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Release Test",
        "-c",
        "user.email=release@example.test",
        "commit",
        "-qm",
        message,
    )
    return git(repo, "rev-parse", "HEAD")


def fixture(tmp_path: Path) -> tuple[Path, dict]:
    repo = tmp_path / "checkout"
    (repo / "core").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "evidence").mkdir()
    (repo / "core" / "engine.py").write_text("RESULT = 1\n")
    (repo / "core" / "README.md").write_text("First API description.\n")
    (repo / "docs" / "note.md").write_text("First description.\n")
    (repo / ".gitignore").write_text("core/engine.py\n")
    proof = repo / "evidence" / "proof.txt"
    proof.write_text("An unchanged example evidence file.\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-f", "core/engine.py")  # Tracked files stay visible even if an ignore rule matches.
    source_commit = commit(repo, "initial input and evidence")

    document = json.loads((ROOT / "evidence" / "product_release.json").read_text())
    document["engineering_complete"] = True
    digest = hashlib.sha256(proof.read_bytes()).hexdigest()
    for gate in document["gates"].values():
        gate.update(
            status="PASS",
            commit=source_commit,
            executed_at="2026-09-23T12:00:00Z",
            commands=[{"command": "offline_test_fixture", "exit_code": 0}],
            evidence_files=[{"path": "evidence/proof.txt", "sha256": digest}],
        )
    return repo, document


def test_current_pass_source_and_evidence_are_accepted(tmp_path: Path) -> None:
    repo, document = fixture(tmp_path)
    assert check_release(document, repo) == []
    assert check_current_revision(document, repo) == []


def test_old_pass_rejected_after_committed_code_change_despite_unchanged_evidence(tmp_path: Path) -> None:
    repo, document = fixture(tmp_path)
    (repo / "core" / "engine.py").write_text("RESULT = 2\n")
    commit(repo, "change product input")
    assert check_release(document, repo) == []  # Hash and self-declared exit code still look valid.
    errors = check_current_revision(document, repo)
    assert len(errors) == len(document["gates"])
    assert all("stale PASS evidence" in error for error in errors)


def test_documentation_commit_does_not_invalidate_same_inputs(tmp_path: Path) -> None:
    repo, document = fixture(tmp_path)
    (repo / "docs" / "note.md").write_text("Revised description.\n")
    (repo / "core" / "README.md").write_text("Revised API description.\n")
    commit(repo, "document evidence")
    assert check_current_revision(document, repo) == []


def test_uncommitted_markdown_inside_controlled_directory_is_documentation(tmp_path: Path) -> None:
    repo, document = fixture(tmp_path)
    (repo / "core" / "README.md").write_text("Work in progress description.\n")
    assert check_current_revision(document, repo) == []


def test_unknown_or_unrelated_commit_is_rejected(tmp_path: Path) -> None:
    repo, document = fixture(tmp_path)
    original = git(repo, "rev-parse", "HEAD")
    document["gates"]["GATE-GRAPH"]["commit"] = "f" * 40
    assert any("unknown Git commit" in error for error in check_current_revision(document, repo))

    git(repo, "switch", "-q", "-c", "side")
    (repo / "docs" / "note.md").write_text("Side branch.\n")
    side = commit(repo, "unmerged branch")
    git(repo, "switch", "-q", "main")
    assert git(repo, "rev-parse", "HEAD") == original
    document["gates"]["GATE-GRAPH"]["commit"] = side
    assert any("not an ancestor" in error for error in check_current_revision(document, repo))


def test_uncommitted_and_untracked_product_inputs_are_rejected(tmp_path: Path) -> None:
    repo, document = fixture(tmp_path)
    (repo / "core" / "engine.py").write_text("RESULT = 2\n")
    assert any(
        "uncommitted or untracked controlled inputs" in error
        for error in check_current_revision(document, repo)
    )
    (repo / "core" / "engine.py").write_text("RESULT = 1\n")
    (repo / "core" / "new_module.py").write_text("NEW = True\n")
    assert any(
        "uncommitted or untracked controlled inputs" in error
        for error in check_current_revision(document, repo)
    )
