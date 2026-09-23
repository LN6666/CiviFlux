"""Check publishable files without printing credential-like content.

This is a bounded repository hygiene check, not a comprehensive security audit.
Ignored raw data, virtual environments, runtime caches and credentials stay local.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{50,}\b"),
    re.compile(rb"(?im)^(?:DASHSCOPE_API_KEY|FEATHERLESS_API_KEY|OPENAI_API_KEY)[ \t]*=[ \t]*[^\s#]{12,}"),
)


def main() -> int:
    names = (
        subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    errors = []
    count = 0
    for name in sorted(set(names) - {""}):
        path = ROOT / name
        if not path.exists():
            continue
        if path.is_symlink():
            errors.append({"path": name, "reason": "symlink requires explicit publication review"})
            continue
        if not path.is_file():
            continue
        count += 1
        if path.stat().st_size > 25 * 1024 * 1024:
            errors.append({"path": name, "reason": "oversized source-controlled file"})
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            errors.append({"path": name, "reason": "environment credentials file"})
        if any(pattern.search(path.read_bytes()) for pattern in SECRET_PATTERNS):
            errors.append({"path": name, "reason": "credential-like content; value redacted"})
    report = {
        "status": "FAIL" if errors else "PASS",
        "files_checked": count,
        "issues": errors,
        "scope": "tracked and publishable untracked files; heuristic secrets, symlinks and size",
    }
    print(json.dumps(report, indent=2))
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
