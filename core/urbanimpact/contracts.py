"""Canonical wire models; ontology registries are loaded from manifest.yaml."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

import yaml
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

MANIFEST_PATH = Path(__file__).resolve().parents[2] / "ontology" / "manifest.yaml"
# Installed source checkout is the reference deployment; wheel includes ontology package.
if not MANIFEST_PATH.exists():
    import ontology

    MANIFEST_PATH = Path(ontology.__file__).parent / "manifest.yaml"
MANIFEST = yaml.safe_load(MANIFEST_PATH.read_text())
ObjectType = Enum("ObjectType", {x["name"]: x["name"] for x in MANIFEST["object_types"]}, type=str)
LinkType = Enum("LinkType", {x["name"]: x["name"] for x in MANIFEST["link_types"]}, type=str)
ActionType = Enum("ActionType", {x["name"]: x["name"] for x in MANIFEST["action_types"]}, type=str)
Id = Annotated[str, Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_:.@+\-/]+$")]
VehicleClass = Literal[
    "passenger", "bus", "emergency", "delivery", "truck", "bicycle", "pedestrian", "taxi", "motorcycle"
]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False, validate_default=True)


class Window(Model):
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def ordered(self):
        if self.start >= self.end:
            raise ValueError("Window requires start < end")
        return self


class Restriction(Model):
    id: Id
    edge_ids: tuple[Id, ...] = Field(min_length=1)
    valid_from: AwareDatetime
    valid_to: AwareDatetime
    blocked_classes: tuple[VehicleClass, ...] = Field(min_length=1)
    evidence_kind: Literal["observed", "announced", "assumed"]
    evidence_refs: tuple[Id, ...] = Field(min_length=1)
    restriction_type: Literal["closure"] = "closure"

    @model_validator(mode="after")
    def ordered(self):
        if self.valid_from >= self.valid_to:
            raise ValueError("Restriction requires valid_from < valid_to")
        if len(set(self.edge_ids)) != len(self.edge_ids):
            raise ValueError("Duplicate edge IDs")
        return self


class Assumption(Model):
    id: Id
    description: str = Field(min_length=1, max_length=2000)
    affects: tuple[str, ...] = Field(min_length=1)


class Incident(Model):
    source_refs: tuple[Id, ...] = Field(min_length=1)
    location_text: str = Field(min_length=1, max_length=500)
    geometry_ref: str = Field(min_length=1, max_length=500)
    geometry_status: Literal["verified", "assumed", "uncertain"]
    notification_time: AwareDatetime | None = None
    point: tuple[float, float] | None = None
    perimeter_source: Literal["user", "imported"] | None = None
    perimeter: dict[str, Any] | None = None

    @model_validator(mode="after")
    def geometry(self):
        if self.point and not (-180 <= self.point[0] <= 180 and -90 <= self.point[1] <= 90):
            raise ValueError("Invalid longitude/latitude")
        if self.perimeter is not None and self.perimeter_source is None:
            raise ValueError("Perimeter needs explicit source")
        return self


class SeedSpec(Model):
    entity_ids: tuple[Id, ...] = Field(min_length=1)
    same_for_pair: Literal[True] = True

    @field_validator("entity_ids")
    @classmethod
    def unique(cls, v):
        if len(v) != len(set(v)):
            raise ValueError("Duplicate seeds")
        return v


class Scenario(Model):
    schema_version: Literal["1.0"] = "1.0"
    ontology_version: Literal["1.0.0"] = "1.0.0"
    scenario_id: Id
    citypack_id: Id
    kind: Literal["road", "fire"]
    timezone: str = "Europe/Helsinki"
    analysis_at: AwareDatetime
    window: Window
    restrictions: tuple[Restriction, ...] = ()
    incident: Incident | None = None
    assumptions: tuple[Assumption, ...] = ()
    objective: Literal["facility_access", "transit_association", "road_disruption"] = "facility_access"
    engine: Literal["routing", "routing_sumo"] = "routing"
    ranking: Literal["A0", "A1", "A2", "A3", "A4", "A5"] = "A2"
    seed_spec: SeedSpec
    analysis_vehicle_class: VehicleClass = "passenger"

    @model_validator(mode="after")
    def consistent(self):
        ZoneInfo(self.timezone)
        if not self.window.start <= self.analysis_at < self.window.end:
            raise ValueError("analysis_at outside analysis window")
        if self.kind == "fire" and self.incident is None:
            raise ValueError("Fire requires an explicitly located incident")
        ids = [x.id for x in self.restrictions]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate restriction IDs")
        if any(x.evidence_kind == "assumed" for x in self.restrictions) and not self.assumptions:
            raise ValueError("Assumed restrictions require declared assumptions")
        return self


class Node(Model):
    id: Id
    lon: float
    lat: float


class Edge(Model):
    id: Id
    source: Id
    target: Id
    length_m: Positive
    speed_kph: Positive
    allowed_vehicle_classes: tuple[VehicleClass, ...]
    geometry: tuple[tuple[float, float], ...] = ()
    source_id: str
    external_id: str
    name: str = ""
    oneway: bool = True
    access_evidence: str = "imported"
    cost_s: Positive | None = None

    @property
    def travel_time_s(self) -> float:
        return self.cost_s if self.cost_s is not None else self.length_m / (self.speed_kph / 3.6)


class Connection(Model):
    from_edge: Id
    to_edge: Id
    allowed_vehicle_classes: tuple[VehicleClass, ...]


class Facility(Model):
    id: Id
    type: Literal["Facility", "Hospital", "FireStation"]
    name: str
    lon: float
    lat: float
    entrance_node_id: Id | None
    source_id: str
    external_id: str
    snap_distance_m: NonNegative | None = None
    access_status: Literal["verified", "candidate", "unknown"] = "candidate"


class Source(Model):
    id: Id
    url: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    retrieved_at: str
    license: str
    path: str | None = None


class CityPack(Model):
    schema_version: Literal["1.0"] = "1.0"
    citypack_id: Id
    timezone: str = "Europe/Helsinki"
    network_temporality: Literal["synthetic", "current_snapshot", "historical"]
    transit_temporality: Literal["synthetic", "current_schedule", "historical", "unavailable"]
    sources: tuple[Source, ...]
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    connections: tuple[Connection, ...] | None = None
    facilities: tuple[Facility, ...] = ()
    transit: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def refs(self):
        nodes = {n.id for n in self.nodes}
        edges = {e.id for e in self.edges}
        source_ids = {s.id for s in self.sources}
        if len(source_ids) != len(self.sources):
            raise ValueError("Duplicate source IDs")
        if any(e.source_id not in source_ids for e in self.edges):
            raise ValueError("Unknown edge source")
        if any(f.source_id not in source_ids for f in self.facilities):
            raise ValueError("Unknown facility source")
        all_ids = [n.id for n in self.nodes] + [e.id for e in self.edges] + [f.id for f in self.facilities]
        for route in self.transit.get("routes", []):
            if "id" not in route:
                raise ValueError("Transit route requires namespaced identity")
            if route.get("source_id") not in source_ids:
                raise ValueError("Unknown transit source")
            all_ids.append(route["id"])
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("Cross-type or duplicate object IDs")
        if len(nodes) != len(self.nodes) or len(edges) != len(self.edges):
            raise ValueError("Duplicate IDs")
        if not edges or not nodes or not self.sources:
            raise ValueError("Citypack needs network and sources")
        if any(e.source not in nodes or e.target not in nodes for e in self.edges):
            raise ValueError("Unknown node")
        if self.connections is not None:
            emap = {e.id: e for e in self.edges}
            for c in self.connections:
                if c.from_edge not in edges or c.to_edge not in edges:
                    raise ValueError("Unknown turn edge")
                if emap[c.from_edge].target != emap[c.to_edge].source:
                    raise ValueError("Disconnected turn")
        for f in self.facilities:
            if f.entrance_node_id is not None and f.entrance_node_id not in nodes:
                raise ValueError("Unknown facility entrance")
        return self


class Temporal(Model):
    valid_from: AwareDatetime | None = None
    valid_to: AwareDatetime | None = None

    @model_validator(mode="after")
    def interval(self):
        if self.valid_from and self.valid_to and self.valid_from >= self.valid_to:
            raise ValueError("Invalid interval")
        return self


class OntologyObject(Model):
    object_id: Id
    object_type: ObjectType
    source_namespace: str
    source_id: str
    valid_time: Temporal = Temporal()
    provenance_refs: tuple[Id, ...] = Field(min_length=1)
    evidence_level: Literal["authoritative/imported", "user_assumed", "derived", "simulated", "model_scored"]
    properties: dict[str, Any] = Field(default_factory=dict)
    geometry_ref: str | None = None


class Link(Model):
    id: Id
    src: Id
    dst: Id
    relation_type: LinkType
    evidence_refs: tuple[Id, ...] = Field(min_length=1)
    asserted_or_derived: Literal["asserted", "derived"]
    derivation_id: str | None = None
    valid_time: Temporal = Temporal()
    confidence_status: Literal["verified", "candidate", "assumed", "unknown"]
    base_strength: NonNegative = 1

    @model_validator(mode="after")
    def derived(self):
        if self.asserted_or_derived == "derived" and not self.derivation_id:
            raise ValueError("Derived link needs derivation")
        return self


class ActionRequest(Model):
    ontology_version: Literal["1.0.0"] = "1.0.0"
    action_id: Id
    action_type: ActionType
    scenario_id: Id
    parameters: dict[str, Any]
    expected_overlay_hash: str | None = None
    actor_context: str = Field(default="local", max_length=100)
    origin: Literal["user", "llm"] = "user"
    user_confirmed: bool = False


class ActionRecord(Model):
    ontology_version: Literal["1.0.0"] = "1.0.0"
    action_id: Id
    action_type: ActionType
    timestamp: AwareDatetime
    parameters_hash: str
    actor_context: str | None
    input_object_refs: tuple[str, ...]
    precondition_results: tuple[dict[str, Any], ...]
    output_object_refs: tuple[str, ...]
    status: Literal["validated", "committed", "rejected", "failed", "cancelled"]
    error: dict[str, Any] | None = None
    provenance_hash: str


class ProjectionSpec(Model):
    projection_id: str
    ontology_version: str = MANIFEST["ontology_version"]
    scenario_id: Id
    analysis_time: AwareDatetime
    time_window: Window
    spatial_scope: Literal["source_citypack_extent"] = "source_citypack_extent"
    max_hops: None = None
    objective: str
    projection_kind: Literal["operational", "dependency_evidence"] = "operational"
    allowed_object_types: tuple[ObjectType, ...]
    allowed_link_types: tuple[LinkType, ...]
    relation_policy_hash: str
    source_snapshot_hash: str

    @model_validator(mode="after")
    def time_scope(self):
        if not self.time_window.start <= self.analysis_time < self.time_window.end:
            raise ValueError("Projection analysis time outside recorded window")
        return self


class Metric(Model):
    value: float | None
    unit: str
    definition_id: str
    scope: str
    evidence_level: str
    uncertainty: str
    status: Literal["available", "unreachable", "unavailable"] = "available"
    numerator: float | None = None
    denominator: float | None = None

    @model_validator(mode="after")
    def missing(self):
        if self.status != "available" and self.value is not None:
            raise ValueError("Missing metric must be null")
        if self.status == "available" and self.value is None:
            raise ValueError("Available metric requires value")
        return self


class ResultBundle(Model):
    schema_version: Literal["1.0"] = "1.0"
    run_id: Id
    scenario_id: Id
    citypack_id: Id
    ontology_version: str
    scenario_overlay_hash: str
    action_log_hash: str
    projection_id: str
    projection_hash: str
    source_snapshot_hash: str
    demand_kind: Literal["synthetic", "estimated", "measured"]
    network_temporality: str
    transit_temporality: str
    simulation_status: str
    provider_mode: Literal[
        "simplejev_demo",
        "simplejev_api",
        "remote_reflex",
        "qwen_api",
        "local_qwen",
        "replay",
        "rules",
        "mock_test",
    ]
    facts: dict[str, Any]
    attention: dict[str, Any]
    graph: dict[str, Any]
    assumptions: tuple[Assumption, ...]
    sources: tuple[Source, ...]
    limitations: tuple[str, ...]
    policy: dict[str, Any] | None = None
