from __future__ import annotations

import hashlib
import math
import re
import subprocess
from pathlib import Path

VEHICLES = (
    "passenger",
    "bus",
    "emergency",
    "delivery",
    "truck",
    "bicycle",
    "pedestrian",
    "taxi",
    "motorcycle",
)


def stable_id(kind: str, external: str) -> str:
    # SUMO identifiers may contain '#' or whitespace, unlike our wire identifiers.
    return (
        f"osm:{kind}:"
        + re.sub(r"[^A-Za-z0-9_:.@+\-/]", "_", external)
        + ":"
        + hashlib.sha256(external.encode()).hexdigest()[:8]
    )


def distance_m(a, b):
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    dlat, dlon = p2 - p1, math.radians(b[0] - a[0])
    return (
        6371008.8
        * 2
        * math.asin(
            min(1, math.sqrt(math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2))
        )
    )


def extract_roi(source: Path, target: Path, bbox: list[float]) -> dict:
    import osmium

    def inside(lon, lat):
        return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]

    selected_ways = set()
    facilities = []
    road_tags = {}
    conditional = []
    with osmium.BackReferenceWriter(
        target, source, overwrite=True, remove_tags=False, relation_depth=3
    ) as writer:
        for obj in osmium.FileProcessor(source).with_locations():
            if obj.is_way():
                points = [[n.lon, n.lat] for n in obj.nodes if n.location.valid()]
                if not points or not any(inside(*p) for p in points):
                    continue
                tags = dict(obj.tags)
                if "highway" in tags:
                    writer.add(obj)
                    selected_ways.add(obj.id)
                    road_tags[str(obj.id)] = tags
                    if any(":conditional" in k for k in tags):
                        conditional.append(str(obj.id))
                if tags.get("amenity") in {"hospital", "fire_station", "clinic", "school"}:
                    # Centroid is explicitly a candidate facility point, never a verified entrance.
                    facilities.append(
                        {
                            "id": stable_id("facility-way", str(obj.id)),
                            "type": {"hospital": "Hospital", "fire_station": "FireStation"}.get(
                                tags["amenity"], "Facility"
                            ),
                            "name": tags.get("name", tags["amenity"]),
                            "lon": sum(p[0] for p in points) / len(points),
                            "lat": sum(p[1] for p in points) / len(points),
                            "source_id": "S03-OSM",
                            "external_id": "way/" + str(obj.id),
                            "entrance_node_id": None,
                            "snap_distance_m": None,
                            "access_status": "candidate",
                        }
                    )
            elif obj.is_node() and obj.location.valid() and inside(obj.lon, obj.lat):
                tags = dict(obj.tags)
                if tags.get("amenity") in {"hospital", "fire_station", "clinic", "school"}:
                    facilities.append(
                        {
                            "id": stable_id("facility-node", str(obj.id)),
                            "type": {"hospital": "Hospital", "fire_station": "FireStation"}.get(
                                tags["amenity"], "Facility"
                            ),
                            "name": tags.get("name", tags["amenity"]),
                            "lon": obj.lon,
                            "lat": obj.lat,
                            "source_id": "S03-OSM",
                            "external_id": "node/" + str(obj.id),
                            "entrance_node_id": None,
                            "snap_distance_m": None,
                            "access_status": "candidate",
                        }
                    )
        restrictions = 0
        for rel in osmium.FileProcessor(source, osmium.osm.RELATION):
            if rel.tags.get("type") == "restriction" and any(
                m.type == "w" and m.ref in selected_ways for m in rel.members
            ):
                writer.add(rel)
                restrictions += 1
    return {
        "bbox": bbox,
        "selected_ways": len(selected_ways),
        "restriction_relations": restrictions,
        "conditional_tag_way_ids": sorted(conditional),
        "road_tags": road_tags,
        "facilities": sorted(facilities, key=lambda x: x["id"]),
    }


def convert_network(
    osm_path: Path,
    output: Path,
    netconvert: Path,
    log_path: Path,
    extraction: dict,
    *,
    source_id: str = "S03-OSM",
) -> dict:
    import sumolib

    command = [
        str(netconvert),
        "--osm-files",
        str(osm_path),
        "--output-file",
        str(output),
        "--keep-edges.by-vclass",
        "passenger,bus,emergency,delivery,truck,taxi,motorcycle",
        "--output.original-names",
        "true",
        "--geometry.remove",
        "true",
        "--no-turnarounds",
        "true",
        "--no-warnings",
        "false",
        "--junctions.corner-detail",
        "0",
        "--seed",
        "42",
    ]
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=180)
        log_path.write_text(process.stdout + "\n" + process.stderr)
    except subprocess.TimeoutExpired as exc:
        log_path.write_text(str(exc))
        raise RuntimeError("BLOCKED_ENVIRONMENT: netconvert exceeded 180-second budget") from exc
    if process.returncode:
        raise RuntimeError(f"netconvert failed ({process.returncode}); see {log_path}")
    net = sumolib.net.readNet(str(output), withInternal=False)
    nodes, edges, connections = [], [], []
    node_ids = {}
    edge_ids = {}
    for node in sorted(net.getNodes(), key=lambda x: x.getID()):
        lon, lat = net.convertXY2LonLat(*node.getCoord())
        identity = stable_id("node", node.getID())
        node_ids[node.getID()] = identity
        nodes.append({"id": identity, "lon": lon, "lat": lat})
    for edge in sorted(net.getEdges(), key=lambda x: x.getID()):
        eid = stable_id("edge", edge.getID())
        edge_ids[edge.getID()] = eid
        external = edge.getID().lstrip("-").split("#")[0]
        tags = extraction["road_tags"].get(external, {})
        raw_conditional = any(":conditional" in k for k in tags)
        edges.append(
            {
                "id": eid,
                "source": node_ids[edge.getFromNode().getID()],
                "target": node_ids[edge.getToNode().getID()],
                "length_m": edge.getLength(),
                "speed_kph": edge.getSpeed() * 3.6,
                "allowed_vehicle_classes": [v for v in VEHICLES if edge.allows(v)],
                "geometry": [list(net.convertXY2LonLat(*p)) for p in edge.getShape()],
                "source_id": source_id,
                "external_id": edge.getID(),
                "name": edge.getName() or tags.get("name", ""),
                "oneway": True,
                "access_evidence": "unverified_conditional_osm_tag"
                if raw_conditional
                else "netconvert_imported_osm_static_and_default_permissions",
            }
        )
    for edge in net.getEdges():
        for target, turns in edge.getOutgoing().items():
            allowed = sorted(
                {
                    v
                    for turn in turns
                    for v in VEHICLES
                    if turn.getFromLane().allows(v) and turn.getToLane().allows(v)
                }
            )
            connections.append(
                {
                    "from_edge": edge_ids[edge.getID()],
                    "to_edge": edge_ids[target.getID()],
                    "allowed_vehicle_classes": allowed,
                }
            )
    eligible_nodes = {e["source"] for e in edges if "passenger" in e["allowed_vehicle_classes"]} | {
        e["target"] for e in edges if "passenger" in e["allowed_vehicle_classes"]
    }
    road_nodes = [n for n in nodes if n["id"] in eligible_nodes]
    facilities = [{**facility, "source_id": source_id} for facility in extraction["facilities"]]
    for facility in facilities:
        point = [facility["lon"], facility["lat"]]
        if road_nodes:
            nearest = min(road_nodes, key=lambda n: distance_m(point, [n["lon"], n["lat"]]))
            dist = distance_m(point, [nearest["lon"], nearest["lat"]])
            facility["snap_distance_m"] = dist
            if dist <= 300:
                facility["entrance_node_id"] = nearest["id"]
            else:
                facility["access_status"] = "unknown"
    return {
        "nodes": nodes,
        "edges": edges,
        "connections": sorted(connections, key=lambda x: (x["from_edge"], x["to_edge"])),
        "facilities": facilities,
        "conversion": {
            "command": command,
            "exit_code": process.returncode,
            "converter": "SUMO netconvert",
            "turns": "SUMO imported OSM restrictions and lane connections; OSM completeness not independently verified",
            "conditional_access": "NOT_VALIDATED",
            "default_speed": "SUMO OSM type defaults where source has no numeric speed",
        },
    }
