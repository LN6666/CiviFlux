"""Object view materialization over immutable inputs and validated scenario overlays.

Audit objects live in the ontology but remain outside ranking projections. This
module is a read model: it never changes a city snapshot, scenario or run.
"""

from ontology.registry import validate_links

from .contracts import CityPack, Link, OntologyObject, Scenario, Temporal
from .graph import city_objects
from .util import digest


def materialize(city: CityPack, scenario: Scenario | None = None, run: dict | None = None):
    if scenario is not None and scenario.citypack_id != city.citypack_id:
        raise ValueError("Scenario and ontology citypack mismatch")
    if run is not None:
        if scenario is None:
            raise ValueError("Run materialization requires its scenario snapshot")
        if (
            run.get("scenario_id") != scenario.scenario_id
            or run.get("citypack_id") != city.citypack_id
            or run.get("source_snapshot_hash") != digest(city)
            or run.get("scenario_overlay_hash") != digest(scenario)
        ):
            raise ValueError("Run and ontology snapshot or overlay mismatch")
    objects = city_objects(city)
    links = []
    source_ids = {s.id for s in city.sources}
    for source in city.sources:
        objects.append(
            OntologyObject(
                object_id="evidence:" + source.id,
                object_type="EvidenceSource",
                source_namespace="source_registry",
                source_id=source.id,
                provenance_refs=(source.id,),
                evidence_level="authoritative/imported",
                properties=source.model_dump(mode="json"),
            )
        )

    def link(src, dst, kind, refs, derivation, confidence="verified", valid_time=None):
        links.append(
            Link(
                id="ontology:" + digest([src, dst, kind, derivation])[:24],
                src=src,
                dst=dst,
                relation_type=kind,
                evidence_refs=refs,
                asserted_or_derived="derived",
                derivation_id=derivation,
                confidence_status=confidence,
                valid_time=valid_time or Temporal(),
            )
        )

    for obj in list(objects):
        if obj.object_type.value == "EvidenceSource":
            continue
        for ref in obj.provenance_refs:
            if ref in source_ids:
                link(obj.object_id, "evidence:" + ref, "SUPPORTED_BY_EVIDENCE", (ref,), "source-registry")
    if scenario:
        sid = "scenario:" + scenario.scenario_id
        refs = tuple(s.id for s in city.sources)
        objects.append(
            OntologyObject(
                object_id=sid,
                object_type="Scenario",
                source_namespace="workspace",
                source_id=scenario.scenario_id,
                provenance_refs=refs,
                evidence_level="user_assumed",
                properties=scenario.model_dump(mode="json"),
                valid_time=Temporal(valid_from=scenario.window.start, valid_to=scenario.window.end),
            )
        )
        for restriction in scenario.restrictions:
            rid = sid + ":restriction:" + restriction.id
            objects.append(
                OntologyObject(
                    object_id=rid,
                    object_type="RoadRestriction",
                    source_namespace="workspace",
                    source_id=restriction.id,
                    provenance_refs=restriction.evidence_refs,
                    evidence_level="user_assumed"
                    if restriction.evidence_kind == "assumed"
                    else "authoritative/imported",
                    properties=restriction.model_dump(mode="json"),
                    valid_time=Temporal(valid_from=restriction.valid_from, valid_to=restriction.valid_to),
                )
            )
            link(
                sid,
                rid,
                "SCENARIO_CONTAINS_RESTRICTION",
                restriction.evidence_refs,
                "validated-action-overlay",
            )
        if scenario.incident:
            iid = sid + ":incident"
            objects.append(
                OntologyObject(
                    object_id=iid,
                    object_type="FireIncident",
                    source_namespace="workspace",
                    source_id=scenario.scenario_id,
                    provenance_refs=scenario.incident.source_refs,
                    evidence_level="authoritative/imported"
                    if scenario.incident.geometry_status == "verified"
                    else "user_assumed",
                    properties=scenario.incident.model_dump(mode="json"),
                    geometry_ref=scenario.incident.geometry_ref,
                )
            )
            for r in scenario.restrictions:
                for eid in r.edge_ids:
                    link(
                        iid,
                        eid,
                        "INCIDENT_RESTRICTS",
                        r.evidence_refs,
                        "scenario-restriction:" + r.id,
                        confidence="assumed" if r.evidence_kind == "assumed" else "verified",
                        valid_time=Temporal(valid_from=r.valid_from, valid_to=r.valid_to),
                    )
        if run:
            if run.get("scenario_id") != scenario.scenario_id or run.get("citypack_id") != city.citypack_id:
                raise ValueError("Run and ontology scope mismatch")
            rid = "run:" + run["run_id"]
            objects.append(
                OntologyObject(
                    object_id=rid,
                    object_type="SimulationRun",
                    source_namespace="analysis",
                    source_id=run["run_id"],
                    provenance_refs=refs,
                    evidence_level="simulated" if run["simulation_status"] == "completed" else "derived",
                    properties={
                        "run_id": run["run_id"],
                        "source_snapshot_hash": run["source_snapshot_hash"],
                        "scenario_overlay_hash": run["scenario_overlay_hash"],
                        "simulation_status": run["simulation_status"],
                    },
                )
            )
            link(rid, sid, "RUN_EVALUATES_SCENARIO", refs, "immutable-run-input")
    validate_links(objects, links)
    return objects, links
