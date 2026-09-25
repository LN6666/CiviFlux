"""Audit pre-event walking/cycling counter coverage near the frozen Berlin map.

The frozen map contains a motor-route prediction. Counter proximity does not turn
it into a walking/cycling prediction or establish observed event impact.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/berlin-active-observation"
MAP = ROOT / "web/public/validation/berlin-mapping-review-local.json"
OUTPUT = ROOT / "evidence/events/berlin-2026-active-observation-coverage.json"
ONSET_LOCAL = "2026-09-26 07:00"
RECENT_CUTOFF_LOCAL = "2026-09-24 00:00"
DISTANCE_BANDS_M = (100, 250, 500, 1000)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> dict[str, dict[str, object]]:
    stations: dict[str, dict[str, object]] = defaultdict(lambda: {"sample_count": 0, "latest_local": ""})
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"segment_id", "date_local", "bike_total", "ped_total"}
        if "ecocounter" in path.name:
            required = {"segment_id", "date_local", "bike_lft", "bike_rgt"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Counter CSV lacks required columns: {path}")
        for row in reader:
            site_id = row["segment_id"]
            date_local = row["date_local"]
            if not site_id or not date_local or date_local >= ONSET_LOCAL:
                if date_local >= ONSET_LOCAL:
                    raise ValueError(f"Counter snapshot is not pre-onset: {path}")
                raise ValueError(f"Counter row lacks ID or local time: {path}")
            item = stations[site_id]
            item["sample_count"] = int(item["sample_count"]) + 1
            item["latest_local"] = max(str(item["latest_local"]), date_local)
    if not stations:
        raise ValueError(f"Counter CSV is empty: {path}")
    return dict(stations)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=MAP)
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()

    map_data = json.loads(args.map.read_text(encoding="utf-8"))
    if map_data.get("status") != "PRE_EVENT_BASELINE_ONLY":
        raise ValueError("Expected the frozen pre-event Berlin map")
    predicted = map_data["layers"]["predicted_route_impact"]["features"]
    inputs = map_data["layers"]["restriction_inputs"]["features"]
    if not predicted or not inputs:
        raise ValueError("Frozen map has no prediction or restriction geometry")
    project = Transformer.from_crs(4326, 25833, always_xy=True).transform
    corridors = {
        "frozen_motor_route_output": unary_union(
            [transform(project, shape(feature["geometry"])) for feature in predicted]
        ),
        "announcement_input_candidates": unary_union(
            [transform(project, shape(feature["geometry"])) for feature in inputs]
        ),
    }
    sources = {}
    for kind in ("ecocounter", "telraam"):
        csv_file = args.raw / f"bzm_{kind}_2026_09.csv.gz"
        geometry_file = args.raw / f"bzm_{kind}_segments.geojson"
        counts = read_csv(csv_file)
        geojson = json.loads(geometry_file.read_text(encoding="utf-8"))
        features = geojson.get("features", [])
        if not features:
            raise ValueError(f"Counter geometry is empty: {geometry_file}")
        seen: set[str] = set()
        matched = []
        for feature in features:
            site_id = str(feature["properties"]["segment_id"])
            if site_id in seen:
                raise ValueError(f"Duplicate counter geometry ID: {site_id}")
            seen.add(site_id)
            if site_id not in counts:
                continue
            geom = transform(project, shape(feature["geometry"]))
            if geom.is_empty or not geom.is_valid:
                raise ValueError(f"Invalid counter geometry: {site_id}")
            matched.append(
                {
                    "id": site_id,
                    "name": feature["properties"].get("siteName")
                    or feature["properties"].get("osm", {}).get("name"),
                    "latest_local": counts[site_id]["latest_local"],
                    "recent": counts[site_id]["latest_local"] >= RECENT_CUTOFF_LOCAL,
                    "counter_quality": [
                        {
                            "status": instance.get("status"),
                            "is_calibration_done": instance.get("is_calibration_done"),
                            "pedestrians_left": instance.get("pedestrians_left"),
                            "pedestrians_right": instance.get("pedestrians_right"),
                            "bikes_left": instance.get("bikes_left"),
                            "bikes_right": instance.get("bikes_right"),
                        }
                        for instance in feature["properties"].get("instance_ids", {}).values()
                    ],
                    "distances_m": {
                        label: round(geom.distance(corridor), 1) for label, corridor in corridors.items()
                    },
                }
            )
        if not matched:
            raise ValueError(f"No counter IDs join to geometry: {kind}")
        coverage = {}
        for label in corridors:
            ranked = sorted(matched, key=lambda item: (item["distances_m"][label], item["id"]))
            nearest = ranked[0]
            coverage[label] = {
                "stations_within_m": {
                    str(band): sum(item["distances_m"][label] <= band for item in matched)
                    for band in DISTANCE_BANDS_M
                },
                "recent_stations_within_m": {
                    str(band): sum(item["recent"] and item["distances_m"][label] <= band for item in matched)
                    for band in DISTANCE_BANDS_M
                },
                "nearest": {
                    "segment_id": nearest["id"],
                    "name": nearest["name"],
                    "distance_m": nearest["distances_m"][label],
                    "latest_sample_local": nearest["latest_local"],
                    "counter_quality": nearest["counter_quality"],
                },
            }
        sources[kind] = {
            "csv_url": f"https://berlin-zaehlt.de/csv/{csv_file.name}",
            "geometry_url": f"https://berlin-zaehlt.de/csv/{geometry_file.name}",
            "csv_sha256": digest(csv_file),
            "geometry_sha256": digest(geometry_file),
            "geometry_features": len(features),
            "stations_with_september_samples": len(counts),
            "stations_joined_to_geometry": len(matched),
            "stations_with_recent_samples": sum(item["recent"] for item in matched),
            "latest_sample_local": max(item["latest_local"] for item in matched),
            "coverage": coverage,
        }

    output = {
        "schema_version": "1.0",
        "status": "PRE_ONSET_OBSERVATION_COVERAGE_ONLY",
        "event_id": "berlin-marathon-2026",
        "onset_local": ONSET_LOCAL,
        "recent_cutoff_local": RECENT_CUTOFF_LOCAL,
        "timezone": "Europe/Berlin",
        "map_sha256": digest(args.map),
        "prediction_sha256": map_data["prediction_sha256"],
        "citypack_sha256": map_data["citypack_sha256"],
        "frozen_motor_route_output_edges": len(predicted),
        "announcement_input_candidate_edges": len(inputs),
        "distance_crs": "EPSG:25833",
        "sources": sources,
        "claim_ceiling": "Station proximity to a frozen motor-route output and announcement input is observation feasibility only. It is not an active-mode prediction, measured closure, event-hour change or segment-level hit rate. Counter data freshness, calibration, mode coverage and spatial representativeness require review before comparison.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": output["status"],
                "sources": {k: v["coverage"]["frozen_motor_route_output"] for k, v in sources.items()},
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
