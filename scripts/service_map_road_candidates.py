"""Build an offline, source-bound directed-road candidate report for Service Map points.

Requires an explicit local CityPack path. Never fetches data, changes the
CityPack, or promotes proximity to verified vehicle access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from urbanimpact.contracts import CityPack
from urbanimpact.util import atomic_json

from adapters.servicemap.road_candidates import assess_road_candidates, inspect_frozen_osm_context

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "evidence/wp1/service_map_entrance_source_snapshot.json"
REPORT = ROOT / "evidence/wp1/service_map_road_candidates.json"
MAX_CITYPACK_BYTES = 64 * 1024 * 1024


def run(citypack_path: Path, output_path: Path = REPORT, *, osm_path: Path | None = None) -> dict:
    citypack_path = citypack_path.expanduser().resolve(strict=True)
    if not citypack_path.is_file() or citypack_path.suffix != ".json":
        raise ValueError("--citypack must name a local JSON file")
    if citypack_path.stat().st_size > MAX_CITYPACK_BYTES:
        raise ValueError("CityPack exceeds offline review input limit")
    snapshot_raw = SNAPSHOT.read_bytes()
    citypack_raw = citypack_path.read_bytes()
    snapshot = json.loads(snapshot_raw)
    citypack = CityPack.model_validate_json(citypack_raw)
    osm_context = inspect_frozen_osm_context(snapshot, osm_path) if osm_path is not None else None
    report = assess_road_candidates(
        snapshot,
        citypack,
        snapshot_sha256=hashlib.sha256(snapshot_raw).hexdigest(),
        citypack_sha256=hashlib.sha256(citypack_raw).hexdigest(),
        osm_context=osm_context,
    )
    atomic_json(output_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--citypack", type=Path, required=True, help="Local frozen Helsinki CityPack JSON")
    parser.add_argument(
        "--osm-pbf", type=Path, help="Optional exact frozen HSL OSM bytes for building/road review"
    )
    parser.add_argument("--output", type=Path, default=REPORT, help="Derived review report path")
    args = parser.parse_args()
    report = run(args.citypack, args.output, osm_path=args.osm_pbf)
    print(
        json.dumps(
            {
                "status": report["status"],
                "case_count": report["case_count"],
                "inspected_official_entrance_count": report["inspected_official_entrance_count"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
