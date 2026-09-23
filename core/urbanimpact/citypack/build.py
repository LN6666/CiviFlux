from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from urbanimpact.citypack.fetch import sha256_file

# Includes the two case areas and an outer urban road belt. This is a bounded ROI,
# not a promise that long-distance diversions are insensitive to the boundary.
BBOX = [24.921, 60.1695, 24.988, 60.193]


def shape_candidates(transit: dict, edges: list[dict]) -> list[dict]:
    from pyproj import Transformer
    from shapely.geometry import LineString
    from shapely.strtree import STRtree

    transform = Transformer.from_crs(4326, 3067, always_xy=True).transform
    usable = [e for e in edges if "bus" in e["allowed_vehicle_classes"] and len(e["geometry"]) >= 2]
    lines = [LineString([transform(*p) for p in e["geometry"]]) for e in usable]
    tree = STRtree(lines)
    route_types = {r["route_id"]: int(r["route_type"]) for r in transit["routes"]}
    matches = []
    for shape in transit["shapes"]:
        if len(shape["coordinates"]) < 2 or not any(
            (route_types.get(r) == 3 or 700 <= route_types.get(r, -1) < 800) for r in shape["route_ids"]
        ):
            continue
        line = LineString([transform(*p) for p in shape["coordinates"]])
        candidates = sorted(
            {usable[int(i)]["id"] for i in tree.query(line, predicate="dwithin", distance=25)}
        )
        matches.append(
            {
                "shape_id": shape["shape_id"],
                "route_ids": ["gtfs:route:" + r for r in shape["route_ids"]],
                "candidate_edge_ids": candidates[:300],
                "total_candidates": len(candidates),
                "truncated": len(candidates) > 300,
                "status": "candidate",
                "method": "projected_geometry_within_25m",
                "crs": "EPSG:3067",
                "evidence_refs": ["S03-OSM", "S03-GTFS"],
                "warning": "Proximity does not establish route use; parallel/directional/temporal ambiguity unresolved.",
            }
        )
    return matches


def build(root: Path) -> dict:
    from adapters.gtfs import inspect_feed
    from adapters.osm import convert_network, extract_roi
    from urbanimpact.contracts import CityPack

    started = time.monotonic()
    out = root / "data/citypacks/helsinki-current"
    out.mkdir(parents=True, exist_ok=True)
    evidence = root / "evidence/wp1"
    evidence.mkdir(parents=True, exist_ok=True)
    sources = []
    for filename in ["hsl.osm.pbf", "hsl.zip"]:
        path = root / "data/raw" / filename
        metadata = json.loads(path.with_suffix(path.suffix + ".source.json").read_text())
        if sha256_file(path) != metadata["sha256"]:
            raise ValueError(f"frozen source hash mismatch: {filename}")
        sources.append(
            {k: metadata[k] for k in ["id", "url", "sha256", "retrieved_at", "license"]}
            | {"path": str(path.relative_to(root))}
        )
    source_hash = hashlib.sha256(
        json.dumps(
            {
                "sources": [s["sha256"] for s in sources],
                "bbox": BBOX,
                "network_policy": "SUMO1.27.1-motor-drivable-v1",
                "importer_revision": "2",
            }
        ).encode()
    ).hexdigest()
    osm_path = out / "helsinki.osm.xml"
    extraction = extract_roi(root / "data/raw/hsl.osm.pbf", osm_path, BBOX)
    (out / "osm_extraction.json").write_text(json.dumps(extraction, ensure_ascii=False, indent=2) + "\n")
    network = convert_network(
        osm_path,
        out / "helsinki.net.xml",
        root / ".venv/bin/netconvert",
        evidence / "netconvert.log",
        extraction,
    )
    transit = inspect_feed(root / "data/raw/hsl.zip", BBOX)
    transit["shape_matches"] = shape_candidates(transit, network["edges"])
    detail_path = out / "transit_schedule_detail.json"
    detail_path.write_text(json.dumps(transit, ensure_ascii=False, separators=(",", ":")) + "\n")
    transit = {
        k: transit[k]
        for k in [
            "source_id",
            "temporality",
            "coverage",
            "stops",
            "routes",
            "total_relevant_trips",
            "shape_match_status",
            "historical_transit_validation",
            "shape_matches",
        ]
    } | {
        "schedule_detail_path": str(detail_path.relative_to(root)),
        "schedule_detail_sha256": sha256_file(detail_path),
    }
    pack = {
        "schema_version": "1.0",
        "citypack_id": "helsinki-current-" + source_hash[:12],
        "timezone": "Europe/Helsinki",
        "network_temporality": "current_snapshot",
        "transit_temporality": "current_schedule",
        "sources": sources,
        **{k: network[k] for k in ["nodes", "edges", "connections", "facilities"]},
        "transit": transit,
        "evidence": {
            "bbox": BBOX,
            "scope": "bounded motor-drivable case belt; broader network retained locally",
            "crs": "EPSG:4326",
            "source_bytes_verified": True,
            "source_license_refs": [
                "https://www.hsl.fi/en/hsl/open-data",
                "https://www.openstreetmap.org/copyright",
            ],
            "network_converter": network["conversion"],
            "osm_restriction_relations": extraction["restriction_relations"],
            "conditional_access_way_ids": extraction["conditional_tag_way_ids"],
            "boundary_stability": "NOT_VALIDATED",
            "facility_mapping": "nearest passenger-road junction within 300m; all unreviewed candidate access points",
            "historical_network": "NOT_VALIDATED",
            "measured_prediction": "NOT_VALIDATED",
            "sumo_network_path": str((out / "helsinki.net.xml").relative_to(root)),
        },
        "warnings": [
            "Reference pack covers a motor-drivable case belt; excludes pedestrian-only/cycle-only roads and long-distance diversions.",
            "Current OSM and GTFS are not historical May 2026 truth.",
            "GTFS geometric associations are candidates, not cancellation or measured-delay evidence.",
            "Facility road snaps are candidate junctions, not verified physical entrances.",
            "OSM conditional access and completeness require review; netconvert defaults are identified, not observed travel times.",
            "ROI boundary sensitivity is not yet validated.",
            "Fire assumptions never establish an actual cordon or safe boundary.",
        ],
    }
    CityPack.model_validate(pack)
    target = out / "citypack.json"
    pending = target.with_suffix(".pending")
    pending.write_text(json.dumps(pack, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
    pending.replace(target)
    feature_collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": e["id"],
                "geometry": {"type": "LineString", "coordinates": e["geometry"]},
                "properties": {
                    k: e[k] for k in ["id", "name", "external_id", "allowed_vehicle_classes", "source_id"]
                },
            }
            for e in pack["edges"]
        ],
    }
    (out / "roads.geojson").write_text(
        json.dumps(feature_collection, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    audit = {
        "status": "PASS_CURRENT_CITYPACK",
        "scope": "frozen current OSM+GTFS bytes, imported SUMO topology/turns, candidate facility/transit association; not historical validation",
        "mode": "real_public_data",
        "command": "python scripts/data_pipeline.py build",
        "exit_code": 0,
        "duration_s": round(time.monotonic() - started, 3),
        "citypack_id": pack["citypack_id"],
        "path": str(target.relative_to(root)),
        "sha256": sha256_file(target),
        "counts": {
            "nodes": len(pack["nodes"]),
            "directed_edges": len(pack["edges"]),
            "turns": len(pack["connections"]),
            "facilities": len(pack["facilities"]),
            "stops": len(transit["stops"]),
            "routes": len(transit["routes"]),
            "shape_matches": len(transit["shape_matches"]),
        },
        "sources": sources,
        "gtfs_coverage": transit["coverage"],
        "blocked_or_unvalidated": [
            "historical_event_network",
            "historical_event_gtfs",
            "independent_measured_traffic_outcomes",
            "human_review_of_directed_road_mapping",
            "verified_facility_entrances",
            "boundary_stability",
        ],
        "artifacts": [
            {"path": str(p.relative_to(root)), "sha256": sha256_file(p)}
            for p in [target, out / "helsinki.net.xml", out / "roads.geojson", out / "osm_extraction.json"]
        ],
    }
    (evidence / "citypack_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    return audit
