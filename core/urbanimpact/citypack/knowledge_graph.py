"""Materialize a source-bound city KG without folding it into a PPR projection.

The immutable CityPack remains authoritative. These gzip JSONL files are local
read models: directed imported turns and candidate facility access are explicit,
typed and provenance-bearing, but not claims of observed traffic operation.
"""

from __future__ import annotations

import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

from urbanimpact.citypack.fetch import sha256_file
from urbanimpact.contracts import CityPack, Link, OntologyObject
from urbanimpact.util import digest


def _line(stream, value: dict) -> None:
    stream.write((json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode())


def _writer(path: Path):
    raw = path.open("wb")
    return raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0)


def export_city_kg(
    city: CityPack,
    objects: list[OntologyObject],
    evidence_links: list[Link],
    directory: Path,
) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    objects_path = directory / "kg_objects.jsonl.gz"
    links_path = directory / "kg_links.jsonl.gz"
    raw, gz = _writer(objects_path)
    try:
        with gz:
            for obj in sorted(objects, key=lambda item: item.object_id):
                _line(gz, obj.model_dump(mode="json"))
    finally:
        raw.close()

    edges = {edge.id: edge for edge in city.edges}
    incident = defaultdict(set)
    for edge in city.edges:
        incident[edge.source].add(edge.id)
        incident[edge.target].add(edge.id)
    counts = Counter()
    skipped_empty_vehicle_scope = 0
    raw, gz = _writer(links_path)
    try:
        with gz:
            for link in sorted(evidence_links, key=lambda item: item.id):
                _line(gz, {"link": link.model_dump(mode="json"), "applicable_vehicle_classes": None})
                counts[link.relation_type.value] += 1
            for turn in city.connections or ():
                src, dst = edges[turn.from_edge], edges[turn.to_edge]
                classes = sorted(
                    set(turn.allowed_vehicle_classes)
                    & set(src.allowed_vehicle_classes)
                    & set(dst.allowed_vehicle_classes)
                )
                if not classes:
                    skipped_empty_vehicle_scope += 1
                    continue
                link = Link(
                    id="kg:" + digest(["ROAD_CONNECTS_TO", src.id, dst.id])[:24],
                    src=src.id,
                    dst=dst.id,
                    relation_type="ROAD_CONNECTS_TO",
                    evidence_refs=tuple(sorted({src.source_id, dst.source_id})),
                    asserted_or_derived="derived",
                    derivation_id="sumo-imported-osm-turn",
                    confidence_status="candidate",
                )
                _line(gz, {"link": link.model_dump(mode="json"), "applicable_vehicle_classes": classes})
                counts["ROAD_CONNECTS_TO"] += 1
            for facility in city.facilities:
                if facility.entrance_node_id is None:
                    continue
                for edge_id in sorted(incident[facility.entrance_node_id]):
                    edge = edges[edge_id]
                    classes = sorted(set(edge.allowed_vehicle_classes) & {"passenger", "bus", "emergency"})
                    if not classes:
                        continue
                    for relation, src, dst in (
                        ("FACILITY_ACCESSED_VIA", facility.id, edge.id),
                        ("SEGMENT_ACCESS_TO_FACILITY", edge.id, facility.id),
                    ):
                        link = Link(
                            id="kg:" + digest([relation, src, dst])[:24],
                            src=src,
                            dst=dst,
                            relation_type=relation,
                            evidence_refs=tuple(sorted({facility.source_id, edge.source_id})),
                            asserted_or_derived="derived",
                            derivation_id="candidate-nearest-road-junction",
                            confidence_status="candidate",
                        )
                        _line(gz, {"link": link.model_dump(mode="json"), "applicable_vehicle_classes": classes})
                        counts[relation] += 1
    finally:
        raw.close()
    return {
        "schema": "civiflux-city-kg-jsonl-v1",
        "citypack_id": city.citypack_id,
        "ontology_version": "1.0.0",
        "objects": len(objects),
        "links_by_type": dict(sorted(counts.items())),
        "skipped_turns_without_common_vehicle_class": skipped_empty_vehicle_scope,
        "artifacts": [
            {"path": path.name, "sha256": sha256_file(path), "size_bytes": path.stat().st_size}
            for path in (objects_path, links_path)
        ],
        "interpretation": "candidate imported topology and facility access; operational PPR projections must re-filter vehicle permissions and scenario time",
    }
