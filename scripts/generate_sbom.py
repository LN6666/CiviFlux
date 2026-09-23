"""Offline, deterministic lockfile SBOM and declared-license evidence inventory.

Generation never downloads packages or infers licensing of bundled native files.
The same locks, installed metadata/binaries and generator produce identical bytes.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import platform
import re
import sys
import tomllib
from importlib import metadata
from pathlib import Path
from urllib.parse import quote

from jsonschema import Draft7Validator
from packaging.licenses import InvalidLicenseExpression, canonicalize_license_expression
from referencing import Registry, Resource

SCHEMA_DIR = Path(__file__).with_name("sbom_schema")
NATIVE_MAGIC = {
    b"\x7fELF",
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
}
LICENSE_NAME = re.compile(r"^(licen[cs]e|copying|notice|copyright)([._-].*|$)", re.IGNORECASE)
LIMITATIONS = [
    "Declared package licensing is metadata evidence, not a legal compatibility conclusion.",
    "All locked platform alternatives are listed; native file hashes cover this installed platform only.",
    "Bundled native-file licenses/versions are not inferred from their parent package; owner notices are retained.",
    "Static libraries and their versions are not fully recoverable from binaries; bundled notices need review.",
    "Host OS, interpreter, system libraries, unpinned build tools and downloaded browsers are outside lock coverage.",
    "City datasets and remote model/provider licensing are outside this software inventory.",
]


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def property_list(**values) -> list[dict]:
    return [{"name": "civiflux:" + key, "value": str(value)} for key, value in sorted(values.items())]


def properties(component: dict) -> dict:
    return {x["name"].removeprefix("civiflux:"): x["value"] for x in component.get("properties", [])}


def python_ref(package: dict) -> str:
    return "pkg:pypi/" + normalize(package["name"]) + "@" + package["version"]


def npm_name(path: str, package: dict) -> str:
    return package.get("name") or path.rsplit("node_modules/", 1)[1]


def npm_ref(path: str, package: dict) -> str:
    return "npm:" + path + "@" + package["version"]


def python_distribution_refs(package: dict) -> list:
    releases = ([package["sdist"]] if package.get("sdist") else []) + package.get("wheels", [])
    return [
        {
            "type": "distribution",
            "url": item["url"],
            "hashes": [{"alg": "SHA-256", "content": item["hash"].split(":", 1)[1]}],
        }
        for item in sorted(releases, key=lambda x: x["url"])
    ]


def npm_hashes(package: dict) -> list:
    result = []
    for integrity in package.get("integrity", "").split():
        algorithm, value = integrity.split("-", 1)
        result.append(
            {
                "alg": {"sha512": "SHA-512", "sha256": "SHA-256", "sha1": "SHA-1"}[algorithm],
                "content": base64.b64decode(value, validate=True).hex(),
            }
        )
    return result


def license_record(ref: str, declared: str | None, source: str, evidence: list) -> dict:
    expression = None
    if declared:
        try:
            expression = str(canonicalize_license_expression(declared))
        except InvalidLicenseExpression:
            pass
    return {
        "component_ref": ref,
        "declared_license": declared,
        "spdx_expression": expression,
        "status": "DECLARED_SPDX" if expression else "UNRESOLVED",
        "source": source,
        "evidence": sorted(evidence, key=lambda x: x["source_path"]),
    }


def component_licenses(record: dict) -> list:
    if record["spdx_expression"]:
        return [{"expression": record["spdx_expression"]}]
    # Do not turn raw text, classifiers or parent-package licenses into an SPDX conclusion.
    return []


def save_text(data: bytes, source: str, texts: dict[str, bytes]) -> dict:
    sha = digest(data)
    target = "texts/" + sha + ".txt"
    texts[target] = data
    return {"source_path": source, "sha256": sha, "text_file": target}


def is_native(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open("rb") as stream:
        magic = stream.read(4)
    return magic in NATIVE_MAGIC or magic[:2] == b"MZ"


def native_candidate(relative: str) -> bool:
    path = Path(relative)
    return (
        path.suffix.lower() in (".so", ".dylib", ".dll", ".pyd", ".node", ".exe")
        or ".so." in path.name
        or "bin" in path.parts
    )


def add_native(
    owner: dict,
    relative: str,
    path: Path,
    components: list,
    licenses: list,
    relations: dict[str, set],
    owner_license: dict,
) -> None:
    if not is_native(path):
        return
    owner_ref = owner["bom-ref"]
    ref = "native:" + digest((owner_ref + ":" + relative).encode())
    components.append(
        {
            "type": "file",
            "bom-ref": ref,
            "name": relative,
            "hashes": [{"alg": "SHA-256", "content": file_hash(path)}],
            "properties": property_list(
                ecosystem="native",
                owner_ref=owner_ref,
                owner_version=owner["version"],
                path=relative,
                license_status="UNRESOLVED",
                version_status="FILE_HASH_ONLY",
            ),
        }
    )
    record = license_record(ref, None, "native file; parent license is not a file-level assertion", [])
    record.update(
        owner_ref=owner_ref,
        owner_license_evidence=owner_license["evidence"],
        reason="Per-file license and embedded component versions require owner notice review",
    )
    licenses.append(record)
    relations.setdefault(owner_ref, set()).add(ref)
    relations[ref] = set()


def python_packages(
    lock: dict,
    components: list,
    licenses: list,
    relations: dict,
    texts: dict,
    distribution=metadata.distribution,
) -> dict:
    installed = {}
    refs_by_name = {}
    for p in lock["package"]:
        refs_by_name.setdefault(normalize(p["name"]), []).append(python_ref(p))
    for package in lock["package"]:
        ref = python_ref(package)
        local = package.get("source", {}).get("editable") == "."
        evidence = []
        try:
            dist = distribution(package["name"])
        except metadata.PackageNotFoundError:
            dist = None
        if dist is not None and dist.version != package["version"]:
            raise ValueError(f"Installed Python version differs from lock: {package['name']}")
        if local:
            continue
        raw_metadata = dist.read_text("METADATA") if dist else None
        if dist:
            declared = dist.metadata.get("License-Expression") or dist.metadata.get("License")
            source = (
                "installed METADATA License-Expression"
                if dist.metadata.get("License-Expression")
                else "installed METADATA License"
            )
            explicit = set(dist.metadata.get_all("License-File", []))
            for file in sorted(dist.files or [], key=str):
                relative = str(file)
                if (
                    LICENSE_NAME.match(Path(relative).name)
                    or relative in explicit
                    or any(relative.endswith("/" + item) for item in explicit)
                ):
                    actual = Path(dist.locate_file(file))
                    if actual.is_file():
                        evidence.append(save_text(actual.read_bytes(), ref + ":" + relative, texts))
            if declared and (len(declared) > 150 or "\n" in declared):
                evidence.append(save_text(declared.encode(), ref + ":METADATA/License", texts))
        else:
            declared, source = None, "not installed for current platform; uv.lock has no license metadata"
        record = license_record(ref, declared, source, evidence)
        if dist:
            record["license_classifiers"] = sorted(
                x for x in dist.metadata.get_all("Classifier", []) if x.startswith("License ::")
            )
        license_evidence = digest(encoded(record))
        component = {
            "type": "library",
            "bom-ref": ref,
            "name": normalize(package["name"]),
            "version": package["version"],
            "purl": ref,
            "licenses": component_licenses(record),
            "properties": property_list(
                ecosystem="pypi",
                lockfile="uv.lock",
                installed=bool(dist),
                license_status=record["status"],
                license_evidence_sha256=license_evidence,
            ),
        }
        if raw_metadata:
            component["properties"] += property_list(metadata_sha256=digest(raw_metadata.encode()))
        component["externalReferences"] = python_distribution_refs(package)
        components.append(component)
        licenses.append(record)
        relations[ref] = set()
        for dep in package.get("dependencies", []):
            candidates = refs_by_name.get(normalize(dep["name"]), [])
            if dep.get("version"):
                candidates = [r for r in candidates if r.endswith("@" + dep["version"])]
            if len(candidates) != 1:
                raise ValueError(f"Ambiguous/missing locked Python dependency: {dep['name']}")
            relations[ref].add(candidates[0])
        if package.get("dependencies"):
            component["properties"] += property_list(
                dependency_markers=json.dumps(package["dependencies"], sort_keys=True)
            )
        if dist:
            for file in sorted(dist.files or [], key=str):
                relative = str(file)
                if not relative.startswith("..") and native_candidate(relative):
                    add_native(
                        component,
                        relative,
                        Path(dist.locate_file(file)),
                        components,
                        licenses,
                        relations,
                        record,
                    )
            installed[ref] = dist.version
    return installed


def resolve_npm(parent: str, name: str, packages: dict) -> str | None:
    # Follow Node's nearest node_modules resolution using locked locations, never name-only deduplication.
    directory = parent
    while True:
        candidate = (directory + "/" if directory else "") + "node_modules/" + name
        if candidate in packages:
            return candidate
        if not directory:
            return None
        directory = directory.rsplit("/node_modules/", 1)[0] if "/node_modules/" in directory else ""


def npm_packages(root: Path, lock: dict, components: list, licenses: list, relations: dict, texts: dict):
    packages = lock["packages"]
    if lock.get("lockfileVersion") != 3:
        raise ValueError("Expected npm lockfileVersion 3")
    for path, package in sorted(packages.items()):
        if not path:
            continue
        if package.get("link") or not package.get("version"):
            raise ValueError("Unresolved linked npm package: " + path)
        ref = npm_ref(path, package)
        actual = root / "web" / path
        evidence = []
        installed = (actual / "package.json").is_file()
        if installed:
            manifest = json.loads((actual / "package.json").read_text())
            if manifest["version"] != package["version"]:
                raise ValueError("Installed npm version differs from lock: " + path)
            for file in sorted(actual.iterdir()):
                if file.is_file() and LICENSE_NAME.match(file.name):
                    evidence.append(save_text(file.read_bytes(), ref + ":" + file.name, texts))
        declared = package.get("license")
        record = license_record(
            ref, declared if isinstance(declared, str) else None, "web/package-lock.json license", evidence
        )
        name = npm_name(path, package)
        component = {
            "type": "library",
            "bom-ref": ref,
            "name": name,
            "version": package["version"],
            "purl": "pkg:npm/" + quote(name, safe="/") + "@" + quote(package["version"], safe=""),
            "licenses": component_licenses(record),
            "properties": property_list(
                ecosystem="npm",
                lockfile="web/package-lock.json",
                path=path,
                installed=installed,
                optional=package.get("optional", False),
                dev=package.get("dev", False),
                license_status=record["status"],
                license_evidence_sha256=digest(encoded(record)),
            ),
        }
        if package.get("resolved"):
            component["externalReferences"] = [{"type": "distribution", "url": package["resolved"]}]
        hashes = npm_hashes(package)
        if hashes:
            component["hashes"] = hashes
        components.append(component)
        licenses.append(record)
        relations[ref] = set()
        for kind in ("dependencies", "optionalDependencies", "peerDependencies"):
            for name in package.get(kind, {}):
                target = resolve_npm(path, name, packages)
                if target is None:
                    if kind == "dependencies":
                        raise ValueError("Missing npm locked dependency: " + path + " -> " + name)
                    continue
                relations[ref].add(npm_ref(target, packages[target]))
        if installed:
            for file in sorted(actual.rglob("*")):
                relative = file.relative_to(actual).as_posix()
                if "node_modules" not in file.relative_to(actual).parts and native_candidate(relative):
                    add_native(component, relative, file, components, licenses, relations, record)


def validate_schema(bom: dict) -> None:
    registry = Registry()
    sources = json.loads((SCHEMA_DIR / "sources.json").read_text())
    for source in sources["sources"]:
        path = SCHEMA_DIR / source["path"]
        if file_hash(path) != source["sha256"]:
            raise ValueError("Vendored CycloneDX schema hash mismatch")
        schema = json.loads(path.read_text())
        resource = Resource.from_contents(schema)
        registry = registry.with_resource("http://cyclonedx.org/schema/" + source["path"], resource)
    schema = json.loads((SCHEMA_DIR / "bom-1.6.schema.json").read_text())
    Draft7Validator(schema, registry=registry).validate(bom)


def validate_locks(bom: dict, root: Path) -> dict:
    py = tomllib.loads((root / "uv.lock").read_text())
    js = json.loads((root / "web/package-lock.json").read_text())
    expected_py = {python_ref(p) for p in py["package"] if p.get("source", {}).get("editable") != "."}
    expected_js = {npm_ref(k, v) for k, v in js["packages"].items() if k}
    seen = {}
    for component in bom["components"]:
        ref = component["bom-ref"]
        if ref in seen:
            raise ValueError("Duplicate SBOM component ref")
        seen[ref] = component
    for ecosystem, expected in (("pypi", expected_py), ("npm", expected_js)):
        actual = {ref for ref, c in seen.items() if properties(c).get("ecosystem") == ecosystem}
        if actual != expected:
            raise ValueError(f"SBOM {ecosystem} lock inventory mismatch")
    for package in py["package"]:
        ref = python_ref(package)
        if ref in seen and (
            seen[ref]["version"] != package["version"] or seen[ref]["name"] != normalize(package["name"])
        ):
            raise ValueError("SBOM Python identity differs from lock")
        if ref in seen and seen[ref].get("externalReferences") != python_distribution_refs(package):
            raise ValueError("SBOM Python artifact hashes or URLs differ from lock")
    for path, package in js["packages"].items():
        if path and (
            seen[npm_ref(path, package)]["version"] != package["version"]
            or seen[npm_ref(path, package)]["name"] != npm_name(path, package)
        ):
            raise ValueError("SBOM npm identity differs from lock")
        if path:
            component = seen[npm_ref(path, package)]
            expected_sources = (
                [{"type": "distribution", "url": package["resolved"]}] if package.get("resolved") else []
            )
            if (
                component.get("hashes", []) != npm_hashes(package)
                or component.get("externalReferences", []) != expected_sources
            ):
                raise ValueError("SBOM npm artifact hash or URL differs from lock")
    inputs = properties(bom["metadata"]["component"])
    for path in ("uv.lock", "web/package-lock.json", "pyproject.toml", "web/package.json"):
        if inputs.get(path + ":sha256") != file_hash(root / path):
            raise ValueError("SBOM lockfile hash mismatch: " + path)
    valid_refs = set(seen) | {bom["metadata"]["component"]["bom-ref"]}
    dependency_refs = [entry["ref"] for entry in bom["dependencies"]]
    if len(set(dependency_refs)) != len(dependency_refs) or set(dependency_refs) != valid_refs:
        raise ValueError("Missing or duplicate dependency inventory")
    for dependency in bom["dependencies"]:
        if dependency["ref"] not in valid_refs or set(dependency["dependsOn"]) - valid_refs:
            raise ValueError("SBOM orphan dependency reference")
    return {
        "python_locked": len(expected_py),
        "npm_locked": len(expected_js),
        "native_files": sum(properties(c).get("ecosystem") == "native" for c in seen.values()),
    }


def build(root: Path, distribution=metadata.distribution) -> dict[str, bytes]:
    py = tomllib.loads((root / "uv.lock").read_text())
    js = json.loads((root / "web/package-lock.json").read_text())
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    components, licenses, texts, relations = [], [], {}, {}
    python_packages(py, components, licenses, relations, texts, distribution)
    npm_packages(root, js, components, licenses, relations, texts)
    root_ref = "application:civiflux@" + project["version"]
    # Root edges identify directly requested application and development dependencies.
    direct = set()
    local = next(p for p in py["package"] if p.get("source", {}).get("editable") == ".")
    by_name = {normalize(p["name"]): python_ref(p) for p in py["package"]}
    for dependency in local.get("dependencies", []):
        direct.add(by_name[normalize(dependency["name"])])
    for group in local.get("dev-dependencies", {}).values():
        direct.update(by_name[normalize(dep["name"])] for dep in group)
    for kind in ("dependencies", "devDependencies", "optionalDependencies"):
        for name in js["packages"][""].get(kind, {}):
            path = resolve_npm("", name, js["packages"])
            if path is None:
                raise ValueError("Missing npm root dependency: " + name)
            direct.add(npm_ref(path, js["packages"][path]))
    relations[root_ref] = direct
    input_hashes = {
        path + ":sha256": file_hash(root / path)
        for path in ("uv.lock", "web/package-lock.json", "pyproject.toml", "web/package.json")
    }
    bom = {
        "$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": root_ref,
                "name": "CiviFlux",
                "version": project["version"],
                "properties": property_list(**input_hashes),
            }
        },
        "components": sorted(components, key=lambda c: c["bom-ref"]),
        "dependencies": [{"ref": ref, "dependsOn": sorted(deps)} for ref, deps in sorted(relations.items())],
        "properties": property_list(
            generator="scripts/generate_sbom.py",
            generator_sha256=file_hash(Path(__file__)),
            observed_platform=platform.system(),
            observed_architecture=platform.machine(),
            scope="all lockfile packages + installed native files; not a complete host SBOM",
            deterministic="no clock, absolute paths or network requests",
        ),
    }
    validate_schema(bom)
    counts = validate_locks(bom, root)
    license_inventory = {
        "status": "INVENTORIED_NOT_LEGALLY_APPROVED",
        "limitations": LIMITATIONS,
        "components": sorted(licenses, key=lambda item: item["component_ref"]),
    }
    unknown = {
        "status": "EXPLICIT_REVIEW_REQUIRED",
        "components": [x for x in license_inventory["components"] if x["status"] == "UNRESOLVED"],
    }
    artifacts = {
        "bom.cdx.json": encoded(bom),
        "license_inventory.json": encoded(license_inventory),
        "unknown_licenses.json": encoded(unknown),
        **texts,
    }
    report = {
        "status": "PASS",
        "scope": "CycloneDX schema, exact lock membership and declared-license evidence inventory",
        "counts": counts,
        "unresolved_licenses": len(unknown["components"]),
        "limitations": LIMITATIONS,
        "input_hashes": input_hashes,
        "artifacts": {name: digest(data) for name, data in sorted(artifacts.items())},
    }
    artifacts["validation.json"] = encoded(report)
    return artifacts


def verify_artifacts(root: Path, out: Path) -> dict:
    report = json.loads((out / "validation.json").read_text())
    for name, sha in report["artifacts"].items():
        if Path(name).is_absolute() or ".." in Path(name).parts or file_hash(out / name) != sha:
            raise ValueError("SBOM evidence artifact integrity mismatch: " + name)
    bom = json.loads((out / "bom.cdx.json").read_text())
    validate_schema(bom)
    return validate_locks(bom, root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, default=Path("evidence/wp7/sbom"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="Check saved artifacts and exact regeneration; write nothing"
    )
    mode.add_argument(
        "--check-locks",
        action="store_true",
        help="Portable saved schema/evidence/lock check only; does not inspect this host's native files",
    )
    args = parser.parse_args()
    try:
        if args.check_locks:
            counts = verify_artifacts(args.root.resolve(), args.out)
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "counts": counts,
                        "scope": "saved schema, artifact integrity and lock consistency",
                        "local_native_check": "NOT_REQUESTED",
                    },
                    sort_keys=True,
                )
            )
            return 0
        artifacts = build(args.root.resolve())
        if args.check:
            verify_artifacts(args.root.resolve(), args.out)
            for name, data in artifacts.items():
                if not (args.out / name).is_file() or (args.out / name).read_bytes() != data:
                    raise ValueError("SBOM regeneration differs: " + name)
        else:
            for name, data in artifacts.items():
                path = args.out / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            verify_artifacts(args.root.resolve(), args.out)
        report = json.loads(artifacts["validation.json"])
        print(
            json.dumps(
                {key: report[key] for key in ("status", "counts", "unresolved_licenses")}, sort_keys=True
            )
        )
        return 0
    except (ValueError, OSError, metadata.PackageNotFoundError) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
