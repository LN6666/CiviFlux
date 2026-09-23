"""Offline geometry candidates for reviewing official entrances against directed roads.

Distances and imported permissions narrow a human review queue. They never
establish a usable building-to-road connection, a verified facility identity,
or historical access.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import osmium
from pyproj import Transformer
from shapely.geometry import LineString, Point
from urbanimpact.contracts import CityPack, Edge

from adapters.osm.network import distance_m
from adapters.servicemap.evidence import assess_snapshot

WGS84 = "EPSG:4326"
FINLAND_METRIC = "EPSG:3067"
REVIEW_RADIUS_M = 150.0
MAX_CANDIDATES = 5
OSM_BUILDING_REVIEW_RADIUS_M = 80.0
OSM_SERVICE_REVIEW_RADIUS_M = 40.0
MAX_OSM_INPUT_BYTES = 256 * 1024 * 1024
VEHICLE_CLASSES = ("passenger", "emergency", "pedestrian")
REVIEW_VEHICLE_CLASSES = ("passenger", "emergency")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
BUILDING_REF = re.compile(r"\brak\.\s*(\d+[a-z]?)\b", re.IGNORECASE)


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


def _file_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def inspect_frozen_osm_context(snapshot: dict, osm_path: Path) -> dict[int, dict]:
    """Inspect nearby OSM building outlines and service ways from the exact frozen bytes.

    This remains a geometry review queue. An OSM service way near an official
    entrance is not evidence of a legal or physically connected vehicle path.
    """
    osm_path = osm_path.expanduser().resolve(strict=True)
    if not osm_path.is_file() or osm_path.stat().st_size > MAX_OSM_INPUT_BYTES:
        raise ValueError("Frozen OSM source is missing or exceeds the input limit")
    expected_hash = _validated_hash(snapshot["osm_source"]["sha256"], "frozen OSM")
    if _file_sha256(osm_path) != expected_hash:
        raise ValueError("Frozen OSM bytes differ from the declared source SHA256")

    forward = Transformer.from_crs(WGS84, FINLAND_METRIC, always_xy=True)
    entrances = {
        item["record"]["id"]: Point(
            *forward.transform(float(item["record"]["longitude"]), float(item["record"]["latitude"]))
        )
        for case in snapshot["cases"]
        for item in case["inspected_entrances"]
    }
    if not entrances:
        return {}
    context = {
        entry_id: {"osm_building_candidates": [], "osm_service_way_candidates": []} for entry_id in entrances
    }
    lon_lats = [
        (float(item["record"]["longitude"]), float(item["record"]["latitude"]))
        for case in snapshot["cases"]
        for item in case["inspected_entrances"]
    ]
    # This loose bounding box only avoids projecting unrelated OSM ways. The
    # final distance check below is in EPSG:3067, not longitude/latitude.
    west, east = min(p[0] for p in lon_lats) - 0.003, max(p[0] for p in lon_lats) + 0.003
    south, north = min(p[1] for p in lon_lats) - 0.002, max(p[1] for p in lon_lats) + 0.002

    class _NearbyWays(osmium.SimpleHandler):
        def way(self, way) -> None:
            tags = {tag.k: tag.v for tag in way.tags}
            is_building = "building" in tags
            is_service = tags.get("highway") == "service"
            if not (is_building or is_service):
                return
            try:
                coordinates = [(node.lon, node.lat) for node in way.nodes]
            except (ValueError, RuntimeError, osmium.InvalidLocationError):
                return
            if len(coordinates) < 2:
                return
            if max(p[0] for p in coordinates) < west or min(p[0] for p in coordinates) > east:
                return
            if max(p[1] for p in coordinates) < south or min(p[1] for p in coordinates) > north:
                return
            line = LineString([forward.transform(lon, lat) for lon, lat in coordinates])
            for entry_id, point in entrances.items():
                distance = line.distance(point)
                if is_building and distance <= OSM_BUILDING_REVIEW_RADIUS_M:
                    context[entry_id]["osm_building_candidates"].append(
                        {
                            "osm_way_id": way.id,
                            "name": tags.get("name"),
                            "building": tags["building"],
                            "ref": tags.get("ref"),
                            "distance_to_outline_m": round(distance, 2),
                        }
                    )
                if is_service and distance <= OSM_SERVICE_REVIEW_RADIUS_M:
                    context[entry_id]["osm_service_way_candidates"].append(
                        {
                            "osm_way_id": way.id,
                            "access": tags.get("access"),
                            "vehicle": tags.get("vehicle"),
                            "motor_vehicle": tags.get("motor_vehicle"),
                            "oneway": tags.get("oneway"),
                            "distance_to_osm_line_m": round(distance, 2),
                        }
                    )

    _NearbyWays().apply_file(str(osm_path), locations=True)
    for row in context.values():
        row["osm_building_candidates"].sort(
            key=lambda item: (item["distance_to_outline_m"], item["osm_way_id"])
        )
        row["osm_building_candidates"] = row["osm_building_candidates"][:MAX_CANDIDATES]
        row["osm_service_way_candidates"].sort(
            key=lambda item: (item["distance_to_osm_line_m"], item["osm_way_id"])
        )
        row["osm_service_way_candidates"] = row["osm_service_way_candidates"][:MAX_CANDIDATES]
    return context


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


def _osm_review_for_entrance(
    raw: dict,
    official_unit: dict,
    official_unit_source: dict,
    point: Point,
    roads_by_osm_way: dict[int, list[_ProjectedEdge]],
    reverse: Transformer,
    source_hashes: dict,
) -> dict:
    buildings = raw["osm_building_candidates"]
    service_ways = []
    for service in raw["osm_service_way_candidates"]:
        hits = []
        for road in roads_by_osm_way.get(service["osm_way_id"], []):
            measure = road.line.project(point)
            closest = road.line.interpolate(measure)
            hits.append((point.distance(closest), road.edge.id, road, measure, closest))
        hits.sort(key=lambda hit: (hit[0], hit[1]))
        service_ways.append(
            {
                **service,
                "imported_directed_edges": [
                    _candidate_row(hit, reverse, OSM_SERVICE_REVIEW_RADIUS_M, source_hashes) for hit in hits
                ],
            }
        )

    address = official_unit.get("street_address_fi")
    address_ref = BUILDING_REF.search(address or "")
    address_ref = address_ref.group(1) if address_ref else None
    nearest_ref = buildings[0]["ref"] if buildings else None
    flags = []
    if address_ref and nearest_ref and address_ref.casefold() != nearest_ref.casefold():
        flags.append("OFFICIAL_ADDRESS_NEAREST_OSM_BUILDING_REF_DISAGREES")
    if service_ways and service_ways[0]["imported_directed_edges"]:
        directed = service_ways[0]["imported_directed_edges"]
        if all(
            not (set(edge["imported_allowed_vehicle_classes"]) & set(REVIEW_VEHICLE_CLASSES))
            for edge in directed
        ):
            flags.append("NEAREST_OSM_SERVICE_WAY_LACKS_IMPORTED_PASSENGER_AND_EMERGENCY_PERMISSION")
        if all(
            edge["turn_coverage"] == "CITYPACK_CONNECTION_LIST_PRESENT"
            and all(
                edge[key][vehicle] == 0
                for key in ("incoming_turn_counts", "outgoing_turn_counts")
                for vehicle in REVIEW_VEHICLE_CLASSES
            )
            for edge in directed
        ):
            flags.append("NEAREST_OSM_SERVICE_WAY_HAS_ZERO_IMPORTED_PASSENGER_AND_EMERGENCY_TURNS")
    return {
        "status": "CONFLICTING_SOURCE_CANDIDATE_NOT_VERIFIED" if flags else "CANDIDATE_ONLY_NOT_VERIFIED",
        "official_unit_name": official_unit.get("name_en") or official_unit.get("name_fi"),
        "official_unit_street_address_fi": address,
        "official_unit_address_building_ref": address_ref,
        "official_unit_search_url": official_unit_source["url"],
        "official_unit_search_response_sha256": official_unit_source["response_sha256"],
        "nearest_osm_building_ref": nearest_ref,
        "review_flags": flags,
        "osm_building_candidates": buildings,
        "osm_service_way_candidates": service_ways,
        "building_to_road_vehicle_access_status": "NOT_VERIFIED",
        "claim_boundary": (
            "Official unit addresses, OSM outlines/service ways and imported directed-edge permissions "
            "are separate observations. Geometry proximity does not prove an entrance-to-road path "
            "or real-world vehicle permission."
        ),
    }


def assess_road_candidates(
    snapshot: dict,
    citypack: CityPack,
    *,
    snapshot_sha256: str,
    citypack_sha256: str,
    review_radius_m: float = REVIEW_RADIUS_M,
    max_candidates: int = MAX_CANDIDATES,
    osm_context: dict[int, dict] | None = None,
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
    roads_by_osm_way: dict[int, list[_ProjectedEdge]] = {}
    if osm_context is not None:
        for road in roads:
            if road.edge.source_id != osm_source.id:
                continue
            way_id = re.fullmatch(r"-?(\d+)(?:#\d+)?", road.edge.external_id or "")
            if way_id:
                roads_by_osm_way.setdefault(int(way_id.group(1)), []).append(road)
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
        units_with_sources = {
            unit["id"]: (unit, search) for search in case["unit_searches"] for unit in search["units"]
        }
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
            row = {
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
            if osm_context is not None:
                if official["id"] not in osm_context:
                    raise ValueError("Frozen OSM context lacks an inspected entrance")
                unit, search = units_with_sources[official["unit_id"]]
                row["osm_source_context_review"] = _osm_review_for_entrance(
                    osm_context[official["id"]], unit, search, point, roads_by_osm_way, reverse, source_hashes
                )
            entrances.append(row)
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
        "frozen_osm_geometry_review": "SOURCE_HASH_VERIFIED_CANDIDATES_ONLY"
        if osm_context is not None
        else "NOT_RUN",
        "case_count": len(rows),
        "inspected_official_entrance_count": entrance_count,
        "g102_status": "PARTIAL",
        "g205_status": "PARTIAL",
        "cases": rows,
    }
