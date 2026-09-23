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
        source = r["source_id"]
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
    if {x.value for x in spec.allowed_object_types} - set(profile["allowed_object_types"]):
        raise ValueError("Projection cannot admit audit objects")
    if {x.value for x in spec.allowed_link_types} - set(profile["allowed_link_types"]):
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
    from .network import compile_restrictions, physical_context_hash

    # Cached physical results must describe this exact network and physical scenario input.
    # Their own checksum proves integrity, but cannot prove that they belong to this run.
    expected_context = {
        "network_hash": digest(city),
        "analysis_at": scenario.analysis_at.isoformat(),
        "vehicle_class": scenario.analysis_vehicle_class,
        "restrictions": sorted(compile_restrictions(city, scenario, scenario.analysis_vehicle_class)),
        "physical_context_hash": physical_context_hash(city, scenario),
    }
    for field, expected in expected_context.items():
        if facts.get(field) != expected:
            raise ValueError(f"Physical facts {field} does not match city/scenario context")

    objects = city_objects(city)
    profile = MANIFEST["projections"][0]
    link_inputs = {"baseline": {}, "event": {}, "dependency_evidence": {}}
    edges = {e.id: e for e in city.edges}
    facilities = {f.id: f for f in city.facilities}

    def add(side, src, dst, relation, sources, derivation, confidence="verified"):
        # One semantic edge may be supported by multiple OD routes. Retain all
        # contributors without adding duplicate edges (which would change PPR).
        key = (src, dst, relation)
        entry = link_inputs[side].setdefault(
            key, {"sources": set(), "derivations": set(), "confidence": confidence}
        )
        # A shared semantic edge is only verified when every supporting OD
        # record verifies access; a candidate must not inherit another OD's
        # stronger label because it happened to appear first.
        if confidence == "candidate":
            entry["confidence"] = "candidate"
        entry["sources"].update(sources)
        entry["derivations"].add(derivation)

    blocked = set(expected_context["restrictions"])
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
            add(
                side,
                c.from_edge,
                c.to_edge,
                "ROAD_CONNECTS_TO",
                (edges[c.from_edge].source_id, edges[c.to_edge].source_id),
                "network-connection",
            )
    for od in facts.get("od", []):
        fid = od.get("facility_id")
        if not fid:
            continue
        if fid not in facilities:
            raise ValueError("Physical route references unknown facility")
        derivation = "routing:" + digest(od)
        for side in ("baseline", "event"):
            route = od.get(side, {})
            if route.get("status") != "available":
                continue
            route_edges = route.get("edge_ids", [])
            if any(eid not in edges for eid in route_edges):
                raise ValueError("Physical route references unknown edge")
            route_sources = {facilities[fid].source_id}
            route_sources.update(edges[eid].source_id for eid in route_edges)
            for eid in route_edges:
                add(
                    side,
                    eid,
                    fid,
                    "SEGMENT_ACCESS_TO_FACILITY",
                    route_sources,
                    derivation,
                    "verified" if od.get("entrance_status") == "verified" else "candidate",
                )
                add(
                    side,
                    fid,
                    eid,
                    "FACILITY_ACCESSED_VIA",
                    route_sources,
                    derivation,
                    "verified" if od.get("entrance_status") == "verified" else "candidate",
                )
    # Static alignment belongs to dependency evidence, not a simulated operational bus route.
    for route in city.transit.get("routes", []):
        if route.get("match_status") != "verified":
            continue
        for eid in route.get("edge_ids", []):
            if eid not in edges:
                raise ValueError("Verified transit route references unknown edge")
            add(
                "dependency_evidence",
                route["id"],
                eid,
                "ROUTE_USES_SEGMENT",
                (route["source_id"], edges[eid].source_id),
                "verified-transit-alignment",
            )
            add(
                "dependency_evidence",
                eid,
                route["id"],
                "SEGMENT_USED_BY_ROUTE",
                (route["source_id"], edges[eid].source_id),
                "verified-transit-alignment",
            )
    links = {}
    for side, entries in link_inputs.items():
        links[side] = []
        for (src, dst, relation), entry in sorted(entries.items()):
            derivations = sorted(entry["derivations"])
            derivation = derivations[0] if len(derivations) == 1 else "aggregate:" + digest(derivations)
            links[side].append(
                Link(
                    id="link:" + digest([src, dst, relation])[:24],
                    src=src,
                    dst=dst,
                    relation_type=relation,
                    evidence_refs=tuple(sorted(entry["sources"])),
                    asserted_or_derived="derived",
                    derivation_id=derivation,
                    confidence_status=entry["confidence"],
                )
            )
    pair = {}
    for side, side_links in links.items():
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
            source_snapshot_hash=expected_context["network_hash"],
        )
        pair[side] = project(objects, side_links, spec)
    if pair["baseline"]["node_universe_hash"] != pair["event"]["node_universe_hash"]:
        raise ValueError("Paired graph universe mismatch")
    before = {e["id"]: e for e in pair["baseline"]["links"]}
    after = {e["id"]: e for e in pair["event"]["links"]}
    # OD records are a set of origin/facility observations; their input order is
    # not an evidence change. Preserve duplicate records while canonicalizing it.
    canonical_facts = {**facts}
    if "od" in canonical_facts:
        canonical_facts["od"] = sorted(canonical_facts["od"], key=digest)
    facts_hash = digest(canonical_facts)
    pair["graph_delta_log"] = [
        {"id": i, "before": before.get(i), "after": after.get(i), "facts_hash": facts_hash}
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
