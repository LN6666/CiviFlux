"""Typed ontology projection; semantic edges retain their source and derivation."""

from __future__ import annotations

from collections import deque
from typing import Any

from ontology.registry import validate_links

from .contracts import MANIFEST, CityPack, Link, OntologyObject, ProjectionSpec, Scenario
from .util import digest


def city_objects(city: CityPack) -> list[OntologyObject]:
    objects = []
    for e in city.edges:
        objects.append(
            OntologyObject(
                object_id=e.id,
                object_type="RoadSegment",
                source_namespace="citypack",
                source_id=e.source_id,
                provenance_refs=(e.source_id,),
                evidence_level="authoritative/imported",
                properties={"name": e.name, "unit": "m/s", "evidence_kind": "imported"},
                geometry_ref=e.id,
            )
        )
    for f in city.facilities:
        objects.append(
            OntologyObject(
                object_id=f.id,
                object_type=f.type,
                source_namespace="citypack",
                source_id=f.source_id,
                provenance_refs=(f.source_id,),
                evidence_level="authoritative/imported",
                properties={"name": f.name, "access_status": f.access_status},
                geometry_ref=f.id,
            )
        )
    for r in city.transit.get("routes", []):
        source = r.get("source_id", city.sources[0].id)
        objects.append(
            OntologyObject(
                object_id=r["id"],
                object_type="TransitRoute",
                source_namespace="gtfs",
                source_id=source,
                provenance_refs=(source,),
                evidence_level="authoritative/imported",
                properties=r,
            )
        )
    return objects


def _active(link: Link, scenario: Scenario) -> bool:
    return (link.valid_time.valid_from is None or link.valid_time.valid_from <= scenario.analysis_at) and (
        link.valid_time.valid_to is None or scenario.analysis_at < link.valid_time.valid_to
    )


def project(objects: list[OntologyObject], links: list[Link], spec: ProjectionSpec) -> dict:
    validate_links(objects, links)
    if spec.ontology_version != MANIFEST["ontology_version"]:
        raise ValueError("Ontology version mismatch")
    profiles = {x["name"]: x for x in MANIFEST["projections"]}
    if spec.projection_id not in profiles:
        raise ValueError("Unregistered projection profile")
    profile = profiles[spec.projection_id]
    if set(x.value for x in spec.allowed_object_types) - set(profile["allowed_object_types"]):
        raise ValueError("Projection cannot admit audit objects")
    if set(x.value for x in spec.allowed_link_types) - set(profile["allowed_link_types"]):
        raise ValueError("Projection cannot admit audit links")
    selected = sorted(
        [
            o
            for o in objects
            if o.object_type in spec.allowed_object_types
            and (o.valid_time.valid_from is None or o.valid_time.valid_from <= spec.analysis_time)
            and (o.valid_time.valid_to is None or spec.analysis_time < o.valid_time.valid_to)
        ],
        key=lambda o: o.object_id,
    )
    ids = {o.object_id for o in selected}
    edges = sorted(
        [
            link
            for link in links
            if link.src in ids
            and link.dst in ids
            and link.relation_type in spec.allowed_link_types
            and (link.valid_time.valid_from is None or link.valid_time.valid_from <= spec.analysis_time)
            and (link.valid_time.valid_to is None or spec.analysis_time < link.valid_time.valid_to)
        ],
        key=lambda e: e.id,
    )
    payload = {
        "nodes": [o.model_dump(mode="json") for o in selected],
        "links": [e.model_dump(mode="json") for e in edges],
    }
    return {
        **payload,
        "spec": spec.model_dump(mode="json"),
        "graph_hash": digest(payload),
        "node_universe_hash": digest(sorted(ids)),
    }


def paired_projection(city: CityPack, scenario: Scenario, facts: dict, policy_hash: str) -> dict:
    objects = city_objects(city)
    profile = MANIFEST["projections"][0]
    links = {"baseline": [], "event": [], "dependency_evidence": []}
    link_ids = {side: set() for side in links}
    all_edge_ids = {e.id for e in city.edges}

    def add(side, src, dst, relation, source, derivation, confidence="verified"):
        link = Link(
            id="link:" + digest([src, dst, relation])[:24],
            src=src,
            dst=dst,
            relation_type=relation,
            evidence_refs=(source,),
            asserted_or_derived="derived",
            derivation_id=derivation,
            confidence_status=confidence,
        )
        if link.id not in link_ids[side]:
            links[side].append(link)
            link_ids[side].add(link.id)

    blocked = set(facts.get("restrictions", []))
    # Router-derived connections change only the operational graph; restricted assets remain in U.
    edge_classes = {e.id: set(e.allowed_vehicle_classes) for e in city.edges}
    for c in city.connections or ():
        if (
            scenario.analysis_vehicle_class
            not in set(c.allowed_vehicle_classes) & edge_classes[c.from_edge] & edge_classes[c.to_edge]
        ):
            continue
        for side in ("baseline", "event"):
            if side == "event" and (c.from_edge in blocked or c.to_edge in blocked):
                continue
            add(side, c.from_edge, c.to_edge, "ROAD_CONNECTS_TO", city.sources[0].id, "network-connection")
    for od in facts.get("od", []):
        fid = od.get("facility_id")
        if not fid:
            continue
        for side in ("baseline", "event"):
            route = od.get(side, {})
            if route.get("status") != "available":
                continue
            for eid in route.get("edge_ids", []):
                add(
                    side,
                    eid,
                    fid,
                    "SEGMENT_ACCESS_TO_FACILITY",
                    city.sources[0].id,
                    "routing:" + digest(od),
                    "verified" if od.get("entrance_status") == "verified" else "candidate",
                )
                add(
                    side,
                    fid,
                    eid,
                    "FACILITY_ACCESSED_VIA",
                    city.sources[0].id,
                    "routing:" + digest(od),
                    "verified" if od.get("entrance_status") == "verified" else "candidate",
                )
    # Static alignment belongs to dependency evidence, not a simulated operational bus route.
    for route in city.transit.get("routes", []):
        if route.get("match_status") != "verified":
            continue
        for eid in route.get("edge_ids", []):
            if eid not in all_edge_ids:
                raise ValueError("Verified transit route references unknown edge")
            add(
                "dependency_evidence",
                route["id"],
                eid,
                "ROUTE_USES_SEGMENT",
                route.get("source_id", city.sources[0].id),
                "verified-transit-alignment",
            )
            add(
                "dependency_evidence",
                eid,
                route["id"],
                "SEGMENT_USED_BY_ROUTE",
                route.get("source_id", city.sources[0].id),
                "verified-transit-alignment",
            )
    pair = {}
    for side in links:
        spec = ProjectionSpec(
            projection_id="road_fire_operational",
            projection_kind="dependency_evidence" if side == "dependency_evidence" else "operational",
            scenario_id=scenario.scenario_id,
            analysis_time=scenario.analysis_at,
            time_window=scenario.window,
            objective=scenario.objective,
            allowed_object_types=profile["allowed_object_types"],
            allowed_link_types=profile["allowed_link_types"],
            relation_policy_hash=policy_hash,
            source_snapshot_hash=digest(city),
        )
        pair[side] = project(objects, links[side], spec)
    if pair["baseline"]["node_universe_hash"] != pair["event"]["node_universe_hash"]:
        raise ValueError("Paired graph universe mismatch")
    before = {e["id"]: e for e in pair["baseline"]["links"]}
    after = {e["id"]: e for e in pair["event"]["links"]}
    pair["graph_delta_log"] = [
        {"id": i, "before": before.get(i), "after": after.get(i), "facts_hash": digest(facts)}
        for i in sorted(set(before) | set(after))
        if before.get(i) != after.get(i)
    ]
    pair["projection_hash"] = digest(pair)
    return pair


def witness_paths(
    graph: dict, seeds: list[str], target: str, max_depth=5, max_paths=3
) -> list[dict[str, Any]]:
    adjacency = {}
    for e in graph["links"]:
        adjacency.setdefault(e["src"], []).append(e)
    out = []
    queue = deque((seed, [], {seed}) for seed in sorted(seeds))
    visited = 0
    while queue and len(out) < max_paths and visited < 10000:
        node, path, seen = queue.popleft()
        visited += 1
        if node == target and path:
            out.append(
                {
                    "edge_ids": [e["id"] for e in path],
                    "source_refs": sorted({r for e in path for r in e["evidence_refs"]}),
                    "interpretation": "dependency witness; not physical causality",
                }
            )
        if len(path) >= max_depth:
            continue
        for edge in sorted(adjacency.get(node, []), key=lambda e: e["id"]):
            if edge["dst"] not in seen and len(queue) + visited < 10000:
                queue.append((edge["dst"], path + [edge], seen | {edge["dst"]}))
    return out
