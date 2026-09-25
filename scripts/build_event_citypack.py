#!/usr/bin/env python3
"""Build a frozen, road-only candidate CityPack for an upcoming event.

No network access occurs here. Fetch the registered public extract separately.
The resulting pack is a current-network research snapshot, not observed closure
operation or measured event traffic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT))

from adapters.osm import convert_network, extract_roi
from urbanimpact.citypack.fetch import sha256_file
from urbanimpact.citypack.knowledge_graph import export_city_kg
from urbanimpact.contracts import CityPack
from urbanimpact.ontology import materialize


CASES = {
    "berlin-marathon-2026": {
        "raw_filename": "berlin-20260924.osm.pbf",
        "timezone": "Europe/Berlin",
        # An event-centred road belt. Alternatives outside it are excluded.
        "bbox": [13.24, 52.45, 13.48, 52.56],
        "event_window": "2026-09-26/27",
    },
    "baku-f1-2026": {
        "raw_filename": "azerbaijan-20260918.osm.pbf",
        "timezone": "Asia/Baku",
        # Street circuit and surrounding alternatives; not a complete city.
        "bbox": [49.78, 40.32, 49.96, 40.44],
        "event_window": "2026-09-24/26",
    },
}


def build(root: Path, case_id: str) -> dict:
    config = CASES[case_id]
    raw = root / "data/raw" / config["raw_filename"]
    metadata = json.loads(raw.with_suffix(raw.suffix + ".source.json").read_text())
    if metadata["status"] != "VERIFIED_BYTES" or sha256_file(raw) != metadata["sha256"]:
        raise ValueError("unverified or changed OSM source bytes")
    out = root / "data/citypacks" / case_id
    out.mkdir(parents=True, exist_ok=True)
    osm_xml = out / "roads.osm.xml"
    extraction = extract_roi(raw, osm_xml, config["bbox"])
    (out / "osm_extraction.json").write_text(json.dumps(extraction, ensure_ascii=False) + "\n")
    network = convert_network(
        osm_xml,
        out / "roads.net.xml",
        root / ".venv/bin/netconvert",
        out / "netconvert.log",
        extraction,
        source_id=metadata["id"],
    )
    source = {k: metadata[k] for k in ("id", "url", "sha256", "retrieved_at", "license")}
    source["path"] = str(raw.relative_to(root))
    identity = hashlib.sha256(
        json.dumps(
            [metadata["sha256"], config["bbox"], "SUMO1.27.1-motor-drivable-v1", "event-road-only-v1"],
            separators=(",", ":"),
        ).encode()
    ).hexdigest()[:12]
    data = {
        "schema_version": "1.0",
        "citypack_id": case_id + "-" + identity,
        "timezone": config["timezone"],
        "network_temporality": "current_snapshot",
        "transit_temporality": "unavailable",
        "sources": [source],
        **{key: network[key] for key in ("nodes", "edges", "connections", "facilities")},
        "transit": {"routes": []},
        "evidence": {
            "bbox": config["bbox"],
            "scope": "bounded event-centred motor-road candidate graph",
            "osm_snapshot_last_modified": metadata.get("source_last_modified"),
            "event_window": config["event_window"],
            "historical_network": "NOT_VALIDATED",
            "actual_closure_operation": "NOT_VALIDATED",
            "measured_event_outcome": "NOT_VALIDATED",
            "boundary_stability": "NOT_VALIDATED",
            "facility_mapping": "candidate nearest road junction; no reviewed physical entrances",
            "sumo_network_path": str((out / "roads.net.xml").relative_to(root)),
            "converter": network["conversion"],
            "restriction_relations": extraction["restriction_relations"],
            "conditional_access_way_ids": extraction["conditional_tag_way_ids"],
        },
        "warnings": [
            "Current OSM topology is not observed event-date road operation or historical pre-closure state.",
            "Event-centred crop excludes some diversion alternatives; boundary sensitivity is untested.",
            "Facility road snaps are candidates, not verified entrances.",
            "No GTFS, measured demand, or independent traffic observations are included.",
        ],
    }
    city = CityPack.model_validate(data)
    target = out / "citypack.json"
    pending = target.with_suffix(".pending")
    pending.write_text(json.dumps(city.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")) + "\n")
    pending.replace(target)
    objects, evidence_links = materialize(city)
    kg = export_city_kg(city, objects, evidence_links, out)
    audit = {
        "status": "PASS_CURRENT_ROAD_ONLY_CANDIDATE",
        "case_id": case_id,
        "citypack_id": city.citypack_id,
        "citypack_sha256": sha256_file(target),
        "source_sha256": metadata["sha256"],
        "source_last_modified": metadata.get("source_last_modified"),
        "bbox": config["bbox"],
        "counts": {
            "junctions": len(city.nodes),
            "directed_road_segments": len(city.edges),
            "turn_connections": len(city.connections or ()),
            "candidate_facilities": len(city.facilities),
            "ontology_objects": len(objects),
            "evidence_links": len(evidence_links),
        },
        "knowledge_graph": kg,
        "claim_ceiling": "current ontology-typed road/facility inventory only; no event prediction validated",
        "unresolved": [
            "announced_closure_to_directed_edge_review",
            "actual_closure_operation",
            "independent_measured_event_outcomes",
            "GTFS",
            "boundary_sensitivity",
        ],
    }
    (out / "build_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id", choices=CASES)
    args = parser.parse_args()
    print(json.dumps(build(ROOT, args.case_id), indent=2))
