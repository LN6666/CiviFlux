"""Offline geometry candidates for reviewing official entrances against directed roads.

Distances and imported permissions narrow a human review queue. They never
establish a usable building-to-road connection, a verified facility identity,
or historical access.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pyproj import Transformer
from shapely.geometry import LineString, Point
from urbanimpact.contracts import CityPack, Edge

from adapters.osm.network import distance_m
from adapters.servicemap.evidence import assess_snapshot

WGS84 = "EPSG:4326"
FINLAND_METRIC = "EPSG:3067"
REVIEW_RADIUS_M = 150.0
MAX_CANDIDATES = 5
VEHICLE_CLASSES = ("passenger", "emergency", "pedestrian")
REVIEW_VEHICLE_CLASSES = ("passenger", "emergency")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class _ProjectedEdge:
    edge: Edge
    line: LineString
    incoming_turns: dict[str, int] | None
    outgoing_turns: dict[str, int] | None


def _validated_hash(value: str, label: str) -> str:
    if SHA256.fullmatch(value) is None:
        raise ValueError(f"Invalid {label} SHA256")
    return value


def _projected_edges(citypack: CityPack, forward: Transformer) -> list[_ProjectedEdge]:
    nodes = {node.id: node for node in citypack.nodes}
    incoming = outgoing = None
    if citypack.connections is not None:
        incoming = {edge.id: {vehicle: 0 for vehicle in VEHICLE_CLASSES} for edge in citypack.edges}
        outgoing = {edge.id: {vehicle: 0 for vehicle in VEHICLE_CLASSES} for edge in citypack.edges}
        for connection in citypack.connections:
            for vehicle in VEHICLE_CLASSES:
                if vehicle in connection.allowed_vehicle_classes:
                    incoming[connection.to_edge][vehicle] += 1
                    outgoing[connection.from_edge][vehicle] += 1

    projected = []
    for edge in citypack.edges:
        geometry = edge.geometry or (
            (nodes[edge.source].lon, nodes[edge.source].lat),
            (nodes[edge.target].lon, nodes[edge.target].lat),
        )
        if len(geometry) < 2:
            raise ValueError(f"Road edge {edge.id} has no line geometry")
        line = LineString([forward.transform(lon, lat) for lon, lat in geometry])
        if line.is_empty or line.length <= 0:
            raise ValueError(f"Road edge {edge.id} has degenerate geometry")
        projected.append(
            _ProjectedEdge(
                edge,
                line,
                incoming[edge.id] if incoming is not None else None,
                outgoing[edge.id] if outgoing is not None else None,
            )
        )
    return projected


def _candidate_row(hit: tuple, reverse: Transformer, review_radius_m: float, source_hashes: dict) -> dict:
    separation, _, road, measure, closest = hit
    closest_lon, closest_lat = reverse.transform(closest.x, closest.y)
    edge = road.edge
    return {
        "directed_edge_id": edge.id,
        "external_road_id": edge.external_id,
        "road_name": edge.name,
        "from_node_id": edge.source,
        "to_node_id": edge.target,
        "distance_to_edge_m": round(separation, 2),
        "within_review_radius": separation <= review_radius_m,
        "closest_point_lon_lat": [round(closest_lon, 7), round(closest_lat, 7)],
        "fraction_along_directed_edge": round(measure / road.line.length, 6),
        "imported_allowed_vehicle_classes": list(edge.allowed_vehicle_classes),
        "imported_access_evidence": edge.access_evidence,
        "turn_coverage": (
            "CITYPACK_CONNECTION_LIST_PRESENT"
            if road.incoming_turns is not None
            else "UNKNOWN_CONNECTION_LIST_MISSING"
        ),
        "incoming_turn_counts": road.incoming_turns,
        "outgoing_turn_counts": road.outgoing_turns,
        "road_source_id": edge.source_id,
        "road_source_declared_sha256": source_hashes[edge.source_id],
    }


def assess_road_candidates(
    snapshot: dict,
    citypack: CityPack,
    *,
    snapshot_sha256: str,
    citypack_sha256: str,
    review_radius_m: float = REVIEW_RADIUS_M,
    max_candidates: int = MAX_CANDIDATES,
) -> dict:
    """Return source-bound candidate distances without editing the CityPack.

    Every inspected official entrance is retained, including those belonging
    to a unit whose identity does not match the OSM facility. Candidates are
    ranked by the closest point on the *directed edge geometry*, not a road
    node or a facility centroid. This is a review aid, not a snap operation.
    """
    _validated_hash(snapshot_sha256, "Service Map snapshot")
    _validated_hash(citypack_sha256, "CityPack")
    if not 0 < review_radius_m <= 1000 or not 1 <= max_candidates <= 20:
        raise ValueError("Review radius or candidate limit is out of bounds")
    identity_report = assess_snapshot(snapshot)
    if citypack.network_temporality != "current_snapshot":
        raise ValueError("Only a current-network CityPack can be compared with this source snapshot")
    osm_source = next((source for source in citypack.sources if source.id == "S03-OSM"), None)
    if osm_source is None or osm_source.sha256 != snapshot["osm_source"]["sha256"]:
        raise ValueError("Service Map and CityPack use different frozen OSM source bytes")

    facility_index = {facility.id: facility for facility in citypack.facilities}
    identity_index = {row["facility_id"]: row for row in identity_report["cases"]}
    source_hashes = {source.id: source.sha256 for source in citypack.sources}
    forward = Transformer.from_crs(WGS84, FINLAND_METRIC, always_xy=True)
    reverse = Transformer.from_crs(FINLAND_METRIC, WGS84, always_xy=True)
    roads = _projected_edges(citypack, forward)
    turn_coverage = (
        "CITYPACK_CONNECTION_LIST_PRESENT"
        if citypack.connections is not None
        else "UNKNOWN_CONNECTION_LIST_MISSING"
    )
    rows = []
    for case in snapshot["cases"]:
        source_facility = case["osm_facility"]
        facility_id = source_facility["id"]
        facility = facility_index.get(facility_id)
        if facility is None or facility.external_id != source_facility["external_id"]:
            raise ValueError(f"Frozen OSM facility {facility_id} is absent or has changed identity")
        anchor_distance = distance_m(
            (facility.lon, facility.lat),
            (float(source_facility["longitude"]), float(source_facility["latitude"])),
        )
        if anchor_distance > 0.5:
            raise ValueError(f"Frozen OSM facility {facility_id} anchor differs from CityPack")
        identity = identity_index[facility_id]
        entrances = []
        for inspected in sorted(case["inspected_entrances"], key=lambda item: item["record"]["id"]):
            official = inspected["record"]
            longitude, latitude = float(official["longitude"]), float(official["latitude"])
            point = Point(*forward.transform(longitude, latitude))
            nearest = []
            for road in roads:
                measure = road.line.project(point)
                closest = road.line.interpolate(measure)
                nearest.append((point.distance(closest), road.edge.id, road, measure, closest))
            nearest.sort(key=lambda row: (row[0], row[1]))
            candidate_rows = [
                _candidate_row(hit, reverse, review_radius_m, source_hashes)
                for hit in nearest[:max_candidates]
            ]
            nearest_permitted = {}
            for vehicle in REVIEW_VEHICLE_CLASSES:
                hit = next((hit for hit in nearest if vehicle in hit[2].edge.allowed_vehicle_classes), None)
                nearest_permitted[vehicle] = (
                    _candidate_row(hit, reverse, review_radius_m, source_hashes) if hit is not None else None
                )
            entrances.append(
                {
                    "official_entrance_id": official["id"],
                    "official_unit_id": official["unit_id"],
                    "official_source_url": inspected["url"],
                    "official_response_sha256": inspected["response_sha256"],
                    "official_is_main_entrance": official["is_main_entrance"] == "Y",
                    "official_point_lon_lat": [longitude, latitude],
                    "facility_identity_status": identity["identity_status"],
                    "candidate_directed_edges": candidate_rows,
                    "nearest_imported_vehicle_permitted_edges": nearest_permitted,
                    "road_access_status": "NOT_VERIFIED",
                    "directed_road_node_id": None,
                    "needs_human_review": True,
                }
            )
        rows.append(
            {
                "facility_id": facility_id,
                "osm_external_id": facility.external_id,
                "osm_name": facility.name,
                "facility_identity_status": identity["identity_status"],
                "citypack_candidate_entrance_node_id": facility.entrance_node_id,
                "inspected_official_unit_entrances": entrances,
                "road_access_status": "NOT_VERIFIED",
                "directed_road_node_id": None,
                "needs_human_review": True,
            }
        )
    entrance_count = sum(len(row["inspected_official_unit_entrances"]) for row in rows)
    return {
        "schema_version": "1.0",
        "status": "CANDIDATES_ONLY_NOT_VERIFIED",
        "claim_boundary": (
            f"{entrance_count} inspected current Service Map entrance points and {len(rows)} OSM facility anchors; "
            "directed-edge proximity and imported vehicle/turn permissions only. "
            "No building-to-road link, facility identity, historical access, or usable driveway is verified."
        ),
        "source_snapshot_sha256": snapshot_sha256,
        "service_map_source": {
            "name": identity_report["source"]["name"],
            "license": identity_report["source"]["license"],
            "attribution": identity_report["source"]["attribution"],
            "retrieved_at": identity_report["source"]["retrieved_at"],
        },
        "citypack_sha256": citypack_sha256,
        "osm_source_sha256": osm_source.sha256,
        "osm_source_license": snapshot["osm_source"]["license"],
        "citypack_id": citypack.citypack_id,
        "network_temporality": citypack.network_temporality,
        "turn_coverage": turn_coverage,
        "distance_crs": FINLAND_METRIC,
        "review_radius_m": review_radius_m,
        "max_candidates_per_entrance": max_candidates,
        "case_count": len(rows),
        "inspected_official_entrance_count": entrance_count,
        "g102_status": "PARTIAL",
        "g205_status": "PARTIAL",
        "cases": rows,
    }
