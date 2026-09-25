"""Bounded, explicitly authorized downloads from the registered public sources."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

SOURCES = {
    "osm": {
        "id": "S03-OSM",
        "url": "https://karttapalvelu.storage.hsldev.com/hsl.osm/hsl.osm.pbf",
        "filename": "hsl.osm.pbf",
        "license": "ODbL-1.0",
        "attribution": "© OpenStreetMap contributors; HSL extract",
        "content_types": ["application/octet-stream"],
        "max_bytes": 100_000_000,
    },
    "gtfs": {
        "id": "S03-GTFS",
        "url": "https://infopalvelut.storage.hsldev.com/gtfs/hsl.zip",
        "filename": "hsl.zip",
        "license": "CC-BY-4.0",
        "attribution": "© HSL 2026",
        "content_types": ["application/zip", "application/octet-stream"],
        "max_bytes": 100_000_000,
    },
    "berlin-osm": {
        "id": "DE-BE-OSM-20260924",
        "url": "https://download.geofabrik.de/europe/germany/berlin-260922.osm.pbf",
        "filename": "berlin-20260924.osm.pbf",
        "license": "ODbL-1.0",
        "attribution": "© OpenStreetMap contributors; Geofabrik extract",
        "content_types": ["application/octet-stream"],
        "max_bytes": 110_000_000,
    },
    "baku-osm": {
        "id": "AZ-BAKU-OSM-20260918",
        "url": "https://download.geofabrik.de/asia/azerbaijan-260918.osm.pbf",
        "filename": "azerbaijan-20260918.osm.pbf",
        "license": "ODbL-1.0",
        "attribution": "© OpenStreetMap contributors; Geofabrik extract",
        "content_types": ["application/octet-stream"],
        "max_bytes": 55_000_000,
    },
}
ALLOWED_HOSTS = frozenset(urlsplit(s["url"]).hostname for s in SOURCES.values())


class RegisteredRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urlsplit(newurl)
        if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS or parts.username or parts.password:
            raise ValueError("unregistered download redirect refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(
    source: str,
    destination: Path,
    *,
    allow_egress: bool = False,
    timeout_s: int = 30,
    total_timeout_s: int = 300,
) -> dict:
    if source not in SOURCES:
        raise ValueError("source must be registered")
    spec = SOURCES[source]
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / spec["filename"]
    metadata = target.with_suffix(target.suffix + ".source.json")
    if target.exists() and metadata.exists():
        existing = json.loads(metadata.read_text())
        if existing["sha256"] != sha256_file(target):
            raise ValueError("frozen source hash mismatch; refusing silent replacement")
        return existing
    if not allow_egress:
        raise PermissionError("explicit allow_egress required for public-data download")
    partial = target.with_suffix(target.suffix + ".partial")
    started = time.monotonic()
    try:
        request = Request(spec["url"], headers={"User-Agent": "CiviFlux/0.1 local research data import"})
        with build_opener(RegisteredRedirect()).open(request, timeout=timeout_s) as response:
            ctype = response.headers.get_content_type()
            declared = response.headers.get("Content-Length")
            if ctype not in spec["content_types"]:
                raise ValueError(f"unexpected content type: {ctype}")
            if declared and int(declared) > spec["max_bytes"]:
                raise ValueError("source exceeds configured byte budget")
            size = 0
            with partial.open("wb") as out:
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > spec["max_bytes"] or time.monotonic() - started > total_timeout_s:
                        raise ValueError("download byte/time budget exceeded")
                    out.write(block)
            if declared and size != int(declared):
                raise ValueError("truncated source bytes")
            if not size:
                raise ValueError("empty source")
            record = {key: value for key, value in spec.items() if key not in {"content_types", "max_bytes"}}
            record.update(
                status="VERIFIED_BYTES",
                sha256=sha256_file(partial),
                size_bytes=size,
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                source_last_modified=response.headers.get("Last-Modified"),
                etag=response.headers.get("ETag"),
                content_type=ctype,
                temporality="current_snapshot",
                historical_validation="NOT_VALIDATED",
            )
        os.replace(partial, target)
        metadata.write_text(json.dumps(record, indent=2) + "\n")
        return record
    finally:
        partial.unlink(missing_ok=True)
