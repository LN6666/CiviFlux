"""Build a retrospective Baku plan-to-plan GIS comparison, without observed data.

The circuit organizer's explicitly bounded Pushkin restriction is the only
scenario input. Synthetic OD pairs are fixed in the case card. AYNA's separately
announced street names are read only after both routes have been computed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from urbanimpact.citypack.fetch import sha256_file
from urbanimpact.contracts import CityPack
from urbanimpact.network import Router

CASE = ROOT / "data/event_cases/baku-f1-2026-indirect-plan-case.json"
FACTS = ROOT / "data/event_cases/baku-f1-2026-source-facts.json"
CITY = ROOT / "data/citypacks/baku-f1-2026/citypack.json"
SUMMARY = ROOT / "evidence/events/baku-2026-indirect-plan-comparison.json"
PUBLIC_MAP = ROOT / "web/public/validation/baku-indirect.json"
DISPLAY_BBOX = (49.845, 40.370, 49.866, 40.383)
INPUT_OR_BOUNDARY_NAMES = frozenset({"Puşkin küçəsi", "Neftçilər prospekti"})


def _midpoint(edge: object) -> tuple[float, float]:
    geometry = edge.geometry
    return (
        sum(point[0] for point in geometry) / len(geometry),
        sum(point[1] for point in geometry) / len(geometry),
    )


def _inside(point: tuple[float, float], bbox: tuple[float, float, float, float]) -> bool:
    return bbox[0] <= point[0] <= bbox[2] and bbox[1] <= point[1] <= bbox[3]


def _nearest(nodes: list, coordinate: list[float]) -> tuple[str, float]:
    lon, lat = coordinate
    node = min(nodes, key=lambda n: ((n.lon - lon) * 0.76) ** 2 + (n.lat - lat) ** 2)
    # The local metric is sufficient to report the synthetic point snap gap.
    gap_m = (((node.lon - lon) * 84600) ** 2 + ((node.lat - lat) * 111130) ** 2) ** 0.5
    return node.id, round(gap_m, 1)


def _collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def build(root: Path = ROOT) -> dict:
    case = json.loads((root / CASE.relative_to(ROOT)).read_text())
    facts = json.loads((root / FACTS.relative_to(ROOT)).read_text())
    city_path = root / CITY.relative_to(ROOT)
    if (
        sha256_file(city_path) != case["citypack_sha256"]
        or case["citypack_sha256"] != facts["citypack_sha256"]
    ):
        raise ValueError("Baku CityPack hash mismatch")
    sources = {source["id"]: source for source in facts["sources"]}
    for source_card in (case["closure_input"], case["held_out_announced_detour_streets"]):
        source = sources[source_card["source_id"]]
        local = root / source["local_ignored_path"]
        if (
            sha256_file(local) != source_card["source_sha256"]
            or source_card["source_sha256"] != source["sha256"]
        ):
            raise ValueError(f"source bytes changed: {source['id']}")
    if case["held_out_announced_detour_streets"]["used_to_choose_od_or_restriction"] is not False:
        raise ValueError("AYNA holdout must not enter route inputs")

    city = CityPack.model_validate_json(city_path.read_bytes())
    edge_by_id = {edge.id: edge for edge in city.edges}
    closure = case["closure_input"]
    blocked = frozenset(
        edge.id
        for edge in city.edges
        if edge.name == closure["street_name_in_citypack"]
        and closure["vehicle_class"] in edge.allowed_vehicle_classes
        and _inside(_midpoint(edge), tuple(closure["midpoint_bbox"]))
    )
    if len(blocked) != 12:
        raise ValueError(f"expected 12 fixed-PBF candidate Pushkin edges, got {len(blocked)}")
    usable_ids = {edge.source for edge in city.edges if "bus" in edge.allowed_vehicle_classes} & {
        edge.target for edge in city.edges if "bus" in edge.allowed_vehicle_classes
    }
    usable_nodes = [node for node in city.nodes if node.id in usable_ids]
    router = Router()
    routes = []
    baseline_ids: set[str] = set()
    detour_ids: set[str] = set()
    for spec in case["synthetic_od_pairs"]:
        origin, origin_gap = _nearest(usable_nodes, spec["start_lon_lat"])
        target, target_gap = _nearest(usable_nodes, spec["end_lon_lat"])
        before = router.route(city, origin, target, vehicle_class="bus")
        after = router.route(city, origin, target, vehicle_class="bus", blocked=blocked)
        if not before["reachable"] or not after["reachable"] or not (set(before["edge_ids"]) & blocked):
            raise ValueError(f"synthetic OD no longer crosses the declared closure: {spec['id']}")
        new_ids = set(after["edge_ids"]) - set(before["edge_ids"])
        baseline_ids.update(before["edge_ids"])
        detour_ids.update(new_ids)
        routes.append(
            {
                "id": spec["id"],
                "synthetic": True,
                "origin_node": origin,
                "target_node": target,
                "origin_snap_gap_m": origin_gap,
                "target_snap_gap_m": target_gap,
                "baseline_distance_m": before["distance_m"],
                "conditional_distance_m": after["distance_m"],
                "delta_distance_m": round(after["distance_m"] - before["distance_m"], 1),
                "baseline_freeflow_time_s": before["travel_time_s"],
                "conditional_freeflow_time_s": after["travel_time_s"],
                "delta_freeflow_time_s": round(after["travel_time_s"] - before["travel_time_s"], 1),
                "baseline_uses_candidate_edges": len(set(before["edge_ids"]) & blocked),
                "new_detour_directed_edges": len(new_ids),
            }
        )

    # AYNA is evaluated only after the BCC-only route output exists. Exact
    # street-name agreement is deliberately narrower than route/segment truth.
    announced_names = frozenset(case["held_out_announced_detour_streets"]["exact_citypack_names"])
    independent_names = announced_names - INPUT_OR_BOUNDARY_NAMES
    agreeing_ids = detour_ids & {eid for eid, edge in edge_by_id.items() if edge.name in independent_names}
    observed_names = sorted({edge_by_id[eid].name for eid in agreeing_ids})
    output_summary = {
        "status": "RETROSPECTIVE_INDIRECT_PLAN_COMPARISON",
        "case_id": case["case_id"],
        "citypack_sha256": sha256_file(city_path),
        "case_sha256": sha256_file(root / CASE.relative_to(ROOT)),
        "bcc_notice_sha256": closure["source_sha256"],
        "ayna_notice_sha256": case["held_out_announced_detour_streets"]["source_sha256"],
        "input_candidate_directed_edges": len(blocked),
        "synthetic_od_routes": routes,
        "unique_new_detour_directed_edges": len(detour_ids),
        "ayna_selected_street_names": len(announced_names),
        "ayna_independent_street_names": len(independent_names),
        "indirect_exact_street_name_agreement_edges": len(agreeing_ids),
        "proxy_new_detour_edge_name_overlap_pct": round(100 * len(agreeing_ids) / len(detour_ids), 1)
        if detour_ids
        else None,
        "indirect_exact_street_name_agreement_names": observed_names,
        "not_scored": ["actual_bus_path", "actual_road_closure", "speed_change", "prediction_accuracy"],
        "claim_ceiling": case["claim_ceiling"],
    }

    def feature(edge_id: str, layer: str) -> dict:
        edge = edge_by_id[edge_id]
        return {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": edge.geometry},
            "properties": {"id": edge_id, "name": edge.name, "layer": layer, "source_id": edge.source_id},
        }

    context_ids = [
        edge.id
        for edge in city.edges
        if edge.name and edge.length_m >= 50 and _inside(_midpoint(edge), DISPLAY_BBOX)
    ]
    announcement_ids = [
        edge.id
        for edge in city.edges
        if edge.name in announced_names and _inside(_midpoint(edge), DISPLAY_BBOX)
    ]
    map_bundle = {
        "schema_version": "civiflux-baku-indirect-v1",
        "status": output_summary["status"],
        "case_id": case["case_id"],
        "network_scope": "Motor-drivable OSM/SUMO road network; dedicated cycle-only and pedestrian-only ways are excluded; routing vehicle class is bus",
        "osm_attribution": "© OpenStreetMap contributors; ODbL 1.0; Geofabrik Azerbaijan 2026-09-18 extract",
        "osm_source_sha256": "5134c55378dda62dfe4257b6aa7eec06fe9c67594f7e578bcd6186fbaac5c363",
        "osm_license_url": "https://www.openstreetmap.org/copyright",
        "bbox": DISPLAY_BBOX,
        "summary": output_summary,
        "sources": [
            {"id": "BCC", "url": sources[closure["source_id"]]["url"], "role": "scenario_input_plan"},
            {
                "id": "AYNA",
                "url": sources[case["held_out_announced_detour_streets"]["source_id"]]["url"],
                "role": "held_out_plan_street_names",
            },
        ],
        "layers": {
            "context_roads": _collection([feature(eid, "context") for eid in context_ids]),
            "bcc_pushkin_candidates": _collection([feature(eid, "bcc_input") for eid in sorted(blocked)]),
            "synthetic_baseline": _collection([feature(eid, "baseline") for eid in sorted(baseline_ids)]),
            "synthetic_new_detour": _collection(
                [feature(eid, "conditional_new_detour") for eid in sorted(detour_ids)]
            ),
            "ayna_named_street_candidates": _collection(
                [feature(eid, "ayna_plan_street") for eid in announcement_ids]
            ),
            "street_name_agreement": _collection(
                [feature(eid, "street_name_agreement") for eid in sorted(agreeing_ids)]
            ),
        },
        "comparison_note": "Retrospective BCC-input synthetic routing versus AYNA announcement street names. Name agreement is neither route-level agreement nor actual observed bus/road impact.",
    }
    summary_path = root / SUMMARY.relative_to(ROOT)
    map_path = root / PUBLIC_MAP.relative_to(ROOT)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(output_summary, ensure_ascii=False, indent=2) + "\n")
    map_path.write_text(json.dumps(map_bundle, ensure_ascii=False, separators=(",", ":")) + "\n")
    return output_summary


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
