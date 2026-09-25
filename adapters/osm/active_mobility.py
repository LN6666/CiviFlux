"""Read-only candidate geometry for dedicated walk/cycle links and pedestrian areas.

Routing authority stays in the typed CityPack. This adapter only exposes
provenance-bearing map geometry; it never infers event closures or access changes.
"""

from __future__ import annotations

from pathlib import Path

from urbanimpact.contracts import CityPack

MOTOR_CLASSES = frozenset({"passenger", "bus", "emergency", "delivery", "truck", "taxi", "motorcycle"})


def _inside(point: tuple[float, float], bbox: tuple[float, float, float, float]) -> bool:
    return bbox[0] <= point[0] <= bbox[2] and bbox[1] <= point[1] <= bbox[3]


def dedicated_active_features(
    city: CityPack, bbox: tuple[float, float, float, float]
) -> dict[str, list[dict]]:
    """Separate dedicated foot, bicycle and shared links by imported SUMO permissions."""
    grouped: dict[str, list[dict]] = {"walk_only": [], "cycle_only": [], "walk_cycle": []}
    for edge in city.edges:
        allowed = set(edge.allowed_vehicle_classes)
        walk, cycle = "pedestrian" in allowed, "bicycle" in allowed
        if not (walk or cycle) or allowed & MOTOR_CLASSES:
            continue
        geometry = edge.geometry
        midpoint = (
            sum(point[0] for point in geometry) / len(geometry),
            sum(point[1] for point in geometry) / len(geometry),
        )
        if not _inside(midpoint, bbox):
            continue
        mode = "walk_cycle" if walk and cycle else "walk_only" if walk else "cycle_only"
        grouped[mode].append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": geometry},
                "properties": {
                    "id": edge.id,
                    "name": edge.name,
                    "layer": mode,
                    "source_id": edge.source_id,
                    "candidate_modes": sorted(
                        {"pedestrian" if walk else "", "bicycle" if cycle else ""} - {""}
                    ),
                    "mapping_status": "OSM_SUMO_CANDIDATE_UNREVIEWED",
                },
            }
        )
    for features in grouped.values():
        features.sort(key=lambda item: item["properties"]["id"])
    return grouped


def pedestrian_area_features(
    osm_path: Path, bbox: tuple[float, float, float, float], source_id: str
) -> list[dict]:
    """Expose only explicit OSM highway=pedestrian + area=yes closed ways."""
    import osmium

    features = []
    for obj in osmium.FileProcessor(osm_path).with_locations():
        if not obj.is_way() or obj.tags.get("highway") != "pedestrian" or obj.tags.get("area") != "yes":
            continue
        coordinates = [[node.lon, node.lat] for node in obj.nodes if node.location.valid()]
        if len(coordinates) < 4 or coordinates[0] != coordinates[-1]:
            continue
        centroid = (
            sum(point[0] for point in coordinates) / len(coordinates),
            sum(point[1] for point in coordinates) / len(coordinates),
        )
        if not _inside(centroid, bbox):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [coordinates]},
                "properties": {
                    "id": f"osm:pedestrian-area:{obj.id}",
                    "name": obj.tags.get("name", ""),
                    "layer": "pedestrian_area",
                    "source_id": source_id,
                    "mapping_status": "OSM_AREA_CANDIDATE_UNREVIEWED",
                },
            }
        )
    return sorted(features, key=lambda item: item["properties"]["id"])
