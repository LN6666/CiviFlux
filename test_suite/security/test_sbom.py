"""Independent SBOM checks: locked inventory, package identity, provenance and ambiguity."""

import base64
import json
import socket
import sys
from copy import deepcopy
from email.message import Message
from importlib import metadata
from pathlib import Path

import pytest

from scripts import generate_sbom
from scripts.generate_sbom import build, validate_locks, verify_artifacts


@pytest.fixture
def sample(tmp_path):
    (tmp_path / "web").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname="civiflux"\nversion="0.1.0"\n')
    (tmp_path / "uv.lock").write_text("""version=1
[[package]]
name="civiflux"
version="0.1.0"
source={editable="."}
dependencies=[{name="native-vendor"}]
[[package]]
name="native-vendor"
version="1.0"
source={registry="https://pypi.org/simple"}
wheels=[{url="https://files.pythonhosted.org/vendor.whl", hash="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}]
[[package]]
name="other-platform"
version="2.0"
source={registry="https://pypi.org/simple"}
""")
    integrity = "sha512-" + base64.b64encode(b"\x22" * 64).decode()
    lock = {
        "name": "web",
        "version": "0.1.0",
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "web", "version": "0.1.0", "dependencies": {"a": "1.0.0", "dep": "1.0.0"}},
            "node_modules/a": {
                "version": "1.0.0",
                "license": "MIT",
                "integrity": integrity,
                "resolved": "https://registry.npmjs.org/a/-/a-1.0.0.tgz",
                "dependencies": {"dep": "2.0.0"},
            },
            "node_modules/a/node_modules/dep": {"version": "2.0.0", "license": "BSD-2-Clause"},
            "node_modules/dep": {"version": "1.0.0", "license": "MIT"},
            "node_modules/optional-os": {"version": "3.0.0", "optional": True},
        },
    }
    (tmp_path / "web/package-lock.json").write_text(json.dumps(lock))
    (tmp_path / "web/package.json").write_text(json.dumps(lock["packages"][""]))
    node_dir = tmp_path / "web/node_modules/a"
    (node_dir / "bin").mkdir(parents=True)
    (node_dir / "package.json").write_text('{"name":"a","version":"1.0.0"}')
    (node_dir / "LICENSE").write_text("Package A declared license notice")
    (node_dir / "bin/tool").write_bytes(b"\x7fELF" + b"native npm fixture")
    py_dir = tmp_path / "installed_python"
    py_dir.mkdir()
    (py_dir / "LICENSE").write_text("Python vendor declared license notice")
    (py_dir / "vendor.so").write_bytes(b"\x7fELF" + b"native Python fixture")

    class Distribution:
        version = "1.0"
        files = (Path("LICENSE"), Path("vendor.so"))
        metadata = Message()
        metadata["License-Expression"] = "MIT"

        def locate_file(self, path):
            return py_dir / path

        def read_text(self, name):
            assert name == "METADATA"
            return "Name: native-vendor\nVersion: 1.0\nLicense-Expression: MIT\n"

    dist = Distribution()

    def lookup(name):
        if name == "native-vendor":
            return dist
        raise metadata.PackageNotFoundError(name)

    return tmp_path, lookup, dist


def test_offline_regeneration_is_identical_and_covers_optional_packages(sample, monkeypatch):
    root, lookup, _ = sample

    def reject_network(*args, **kwargs):
        raise AssertionError("SBOM generation must be offline")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    first, second = build(root, lookup), build(root, lookup)
    assert first == second
    report = json.loads(first["validation.json"])
    assert report["counts"] == {"python_locked": 2, "npm_locked": 4, "native_files": 2}
    bom = json.loads(first["bom.cdx.json"])
    assert validate_locks(bom, root) == report["counts"]


@pytest.mark.parametrize(
    "mutation", ["omit_python", "omit_npm", "version", "wheel_hash", "npm_hash", "orphan"]
)
def test_lock_validator_rejects_omissions_and_tampering(sample, mutation):
    root, lookup, _ = sample
    bom = json.loads(build(root, lookup)["bom.cdx.json"])
    vendor = next(c for c in bom["components"] if c["name"] == "native-vendor")
    npm = next(c for c in bom["components"] if c["name"] == "a")
    if mutation == "omit_python":
        bom["components"].remove(vendor)
    elif mutation == "omit_npm":
        bom["components"].remove(npm)
    elif mutation == "version":
        vendor["version"] = "9.9"
    elif mutation == "wheel_hash":
        vendor["externalReferences"][0]["hashes"][0]["content"] = "b" * 64
    elif mutation == "npm_hash":
        npm["hashes"][0]["content"] = "a" * 128
    else:
        bom["dependencies"][0]["dependsOn"].append("not-a-locked-component")
    with pytest.raises(ValueError):
        validate_locks(bom, root)


def test_installed_version_mismatch_is_not_used_for_license_evidence(sample):
    root, lookup, dist = sample
    dist.version = "9.9"
    with pytest.raises(ValueError, match="Installed Python version differs"):
        build(root, lookup)


def test_native_file_does_not_inherit_parent_license_and_unknowns_are_explicit(sample):
    root, lookup, _ = sample
    data = build(root, lookup)
    licenses = json.loads(data["license_inventory.json"])["components"]
    assert (
        next(x for x in licenses if x["component_ref"] == "pkg:pypi/native-vendor@1.0")["spdx_expression"]
        == "MIT"
    )
    natives = [x for x in licenses if x["component_ref"].startswith("native:")]
    assert len(natives) == 2
    assert all(x["spdx_expression"] is None and x["status"] == "UNRESOLVED" for x in natives)
    assert all(x["owner_license_evidence"] for x in natives)
    unknown = {x["component_ref"] for x in json.loads(data["unknown_licenses.json"])["components"]}
    assert "pkg:pypi/other-platform@2.0" in unknown
    assert "npm:node_modules/optional-os@3.0.0" in unknown
    assert {x["component_ref"] for x in natives} <= unknown


def test_nested_npm_versions_remain_distinct_and_resolve_nearest_parent(sample):
    root, lookup, _ = sample
    bom = json.loads(build(root, lookup)["bom.cdx.json"])
    deps = {d["ref"]: d["dependsOn"] for d in bom["dependencies"]}
    assert "npm:node_modules/a/node_modules/dep@2.0.0" in deps["npm:node_modules/a@1.0.0"]
    assert "npm:node_modules/dep@1.0.0" not in deps["npm:node_modules/a@1.0.0"]
    assert "npm:node_modules/dep@1.0.0" in deps["application:civiflux@0.1.0"]


def test_saved_notice_and_native_hash_tampering_invalidates_evidence(sample, tmp_path):
    root, lookup, _ = sample
    data = build(root, lookup)
    out = tmp_path / "output"
    for name, content in data.items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    verify_artifacts(root, out)
    notice = next(out.glob("texts/*.txt"))
    notice.write_text("Modified notice")
    with pytest.raises(ValueError, match="artifact integrity"):
        verify_artifacts(root, out)
    # A changed observed binary must change the regenerated SBOM, independent of its declared package version.
    before = deepcopy(data)
    (root / "installed_python/vendor.so").write_bytes(b"\x7fELFchanged binary")
    assert build(root, lookup)["bom.cdx.json"] != before["bom.cdx.json"]


def test_portable_lock_check_does_not_inspect_other_platform_metadata(sample, monkeypatch, capsys):
    root, lookup, _ = sample
    out = root / "saved"
    for name, content in build(root, lookup).items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def reject_platform_inventory(*args, **kwargs):
        raise AssertionError("Portable lock check must not inventory the current platform")

    monkeypatch.setattr(generate_sbom, "build", reject_platform_inventory)
    monkeypatch.setattr(
        sys, "argv", ["generate_sbom.py", "--root", str(root), "--out", str(out), "--check-locks"]
    )
    assert generate_sbom.main() == 0
    assert json.loads(capsys.readouterr().out)["local_native_check"] == "NOT_REQUESTED"
