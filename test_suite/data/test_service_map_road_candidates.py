"""Geometry candidate audit must preserve identity and physical-access uncertainty."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest
from pyproj import Transformer
from urbanimpact.contracts import CityPack
from urbanimpact.util import digest

from adapters.servicemap.road_candidates import assess_road_candidates, inspect_frozen_osm_context
from scripts import service_map_road_candidates

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "evidence/wp1/service_map_entrance_source_snapshot.json"
REPORT = ROOT / "evidence/wp1/service_map_road_candidates.json"


def _snapshot_case(name: str) -> dict:
    snapshot = copy.deepcopy(json.loads(SNAPSHOT.read_text()))
    snapshot["cases"] = [case for case in snapshot["cases"] if case["osm_facility"]["name"] == name]
    assert len(snapshot["cases"]) == 1
    return snapshot


def _citypack(snapshot: dict) -> CityPack:
    source_facility = snapshot["cases"][0]["osm_facility"]
    official = snapshot["cases"][0]["inspected_entrances"][0]["record"]
    lon, lat = float(official["longitude"]), float(official["latitude"])
    forward = Transformer.from_crs("EPSG:4326", "EPSG:3067", always_xy=True)
    reverse = Transformer.from_crs("EPSG:3067", "EPSG:4326", always_xy=True)
    x, y = forward.transform(lon, lat)
    west = reverse.transform(x - 100, y + 10)
    east = reverse.transform(x + 100, y + 10)
    return CityPack.model_validate(
        {
            "citypack_id": "synthetic-service-road-review",
            "network_temporality": "current_snapshot",
            "transit_temporality": "unavailable",
            "sources": [
                {
                    "id": "S03-OSM",
                    "url": snapshot["osm_source"]["url"],
                    "sha256": snapshot["osm_source"]["sha256"],
                    "retrieved_at": snapshot["osm_source"]["retrieved_at"],
                    "license": "ODbL-1.0",
                }
            ],
            "nodes": [
                {"id": "osm:node:west", "lon": west[0], "lat": west[1]},
                {"id": "osm:node:east", "lon": east[0], "lat": east[1]},
            ],
            "edges": [
                {
                    "id": "osm:edge:eastbound",
                    "source": "osm:node:west",
                    "target": "osm:node:east",
                    "length_m": 200,
                    "speed_kph": 30,
                    "allowed_vehicle_classes": ["passenger", "emergency"],
                    "geometry": [west, east],
                    "source_id": "S03-OSM",
                    "external_id": "test-eastbound",
                    "access_evidence": "synthetic-imported-permission",
                },
                {
                    "id": "osm:edge:westbound",
                    "source": "osm:node:east",
                    "target": "osm:node:west",
                    "length_m": 200,
                    "speed_kph": 30,
                    "allowed_vehicle_classes": ["passenger", "emergency"],
                    "geometry": [east, west],
                    "source_id": "S03-OSM",
                    "external_id": "test-westbound",
                    "access_evidence": "synthetic-imported-permission",
                },
            ],
            "connections": [
                {
                    "from_edge": "osm:edge:eastbound",
                    "to_edge": "osm:edge:westbound",
                    "allowed_vehicle_classes": ["passenger"],
                }
            ],
            "facilities": [
                {
                    "id": source_facility["id"],
                    "type": "Facility",
                    "name": source_facility["name"],
                    "lon": source_facility["longitude"],
                    "lat": source_facility["latitude"],
                    "entrance_node_id": "osm:node:west",
                    "source_id": "S03-OSM",
                    "external_id": source_facility["external_id"],
                    "access_status": "candidate",
                }
            ],
        }
    )


def _assess(
    snapshot: dict, citypack: CityPack, *, max_candidates: int = 2, osm_context: dict[int, dict] | None = None
) -> dict:
    return assess_road_candidates(
        snapshot,
        citypack,
        snapshot_sha256="a" * 64,
        citypack_sha256="b" * 64,
        review_radius_m=20,
        max_candidates=max_candidates,
        osm_context=osm_context,
    )


def test_project_to_directed_edge_not_centroid_or_endpoint_and_keep_review_boundary():
    snapshot = _snapshot_case("Tölö gymnasium")
    citypack = _citypack(snapshot)
    before = digest(citypack)
    report = _assess(snapshot, citypack)
    assert digest(citypack) == before
    assert report["case_count"] == report["inspected_official_entrance_count"] == 1
    assert (report["g102_status"], report["g205_status"]) == ("PARTIAL", "PARTIAL")
    assert report["service_map_source"]["attribution"] == "City of Helsinki Service Map"
    assert report["osm_source_sha256"] == snapshot["osm_source"]["sha256"]
    facility = report["cases"][0]
    assert facility["facility_identity_status"] == "OFFICIAL_UNIT_MATCH_CANDIDATE"
    assert facility["road_access_status"] == "NOT_VERIFIED"
    assert facility["directed_road_node_id"] is None
    entrance = facility["inspected_official_unit_entrances"][0]
    assert entrance["official_entrance_id"] == 19489
    assert entrance["directed_road_node_id"] is None
    assert entrance["needs_human_review"]
    edges = entrance["candidate_directed_edges"]
    assert {edge["directed_edge_id"] for edge in edges} == {
        "osm:edge:eastbound",
        "osm:edge:westbound",
    }
    assert all(9.9 < edge["distance_to_edge_m"] < 10.1 for edge in edges)
    assert all(edge["within_review_radius"] for edge in edges)
    assert all(0.49 < edge["fraction_along_directed_edge"] < 0.51 for edge in edges)
    eastbound = next(edge for edge in edges if edge["directed_edge_id"] == "osm:edge:eastbound")
    westbound = next(edge for edge in edges if edge["directed_edge_id"] == "osm:edge:westbound")
    assert eastbound["from_node_id"] == westbound["to_node_id"]
    assert eastbound["outgoing_turn_counts"] == {"passenger": 1, "emergency": 0, "pedestrian": 0}
    assert westbound["incoming_turn_counts"] == {"passenger": 1, "emergency": 0, "pedestrian": 0}
    assert eastbound["turn_coverage"] == "CITYPACK_CONNECTION_LIST_PRESENT"
    assert eastbound["imported_access_evidence"] == "synthetic-imported-permission"
    assert entrance["nearest_imported_vehicle_permitted_edges"]["passenger"]["directed_edge_id"] in {
        "osm:edge:eastbound",
        "osm:edge:westbound",
    }


def test_missing_connection_list_has_unknown_turn_counts_not_false_zero():
    snapshot = _snapshot_case("Tölö gymnasium")
    citypack = _citypack(snapshot)
    no_turn_data = CityPack.model_validate({**citypack.model_dump(mode="json"), "connections": None})
    report = _assess(snapshot, no_turn_data)
    assert report["turn_coverage"] == "UNKNOWN_CONNECTION_LIST_MISSING"
    entrance = report["cases"][0]["inspected_official_unit_entrances"][0]
    for candidate in entrance["candidate_directed_edges"]:
        assert candidate["turn_coverage"] == "UNKNOWN_CONNECTION_LIST_MISSING"
        assert candidate["incoming_turn_counts"] is None
        assert candidate["outgoing_turn_counts"] is None
    for candidate in entrance["nearest_imported_vehicle_permitted_edges"].values():
        assert candidate["incoming_turn_counts"] is None
        assert candidate["outgoing_turn_counts"] is None


def test_nearest_vehicle_permitted_edge_survives_disallowed_top_five():
    snapshot = _snapshot_case("Tölö gymnasium")
    base = _citypack(snapshot).model_dump(mode="json")
    official = snapshot["cases"][0]["inspected_entrances"][0]["record"]
    forward = Transformer.from_crs("EPSG:4326", "EPSG:3067", always_xy=True)
    reverse = Transformer.from_crs("EPSG:3067", "EPSG:4326", always_xy=True)
    x, y = forward.transform(float(official["longitude"]), float(official["latitude"]))
    for offset in range(1, 6):
        west_id, east_id = f"osm:node:nearwest{offset}", f"osm:node:neareast{offset}"
        west = reverse.transform(x - 100, y + offset)
        east = reverse.transform(x + 100, y + offset)
        base["nodes"].extend(
            [
                {"id": west_id, "lon": west[0], "lat": west[1]},
                {"id": east_id, "lon": east[0], "lat": east[1]},
            ]
        )
        base["edges"].append(
            {
                "id": f"osm:edge:pedestrian{offset}",
                "source": west_id,
                "target": east_id,
                "length_m": 200,
                "speed_kph": 5,
                "allowed_vehicle_classes": ["pedestrian"],
                "geometry": [west, east],
                "source_id": "S03-OSM",
                "external_id": f"test-pedestrian-{offset}",
                "access_evidence": "synthetic-pedestrian-only",
            }
        )
    citypack = CityPack.model_validate(base)
    report = _assess(snapshot, citypack, max_candidates=5)
    entrance = report["cases"][0]["inspected_official_unit_entrances"][0]
    top_five = entrance["candidate_directed_edges"]
    assert len(top_five) == 5
    assert all("passenger" not in edge["imported_allowed_vehicle_classes"] for edge in top_five)
    assert all("emergency" not in edge["imported_allowed_vehicle_classes"] for edge in top_five)
    for vehicle in ("passenger", "emergency"):
        nearest = entrance["nearest_imported_vehicle_permitted_edges"][vehicle]
        assert nearest["directed_edge_id"] not in {edge["directed_edge_id"] for edge in top_five}
        assert nearest["distance_to_edge_m"] == 10.0
        assert nearest["road_source_declared_sha256"] == snapshot["osm_source"]["sha256"]
        assert nearest["turn_coverage"] == "CITYPACK_CONNECTION_LIST_PRESENT"
        assert entrance["road_access_status"] == "NOT_VERIFIED"


def test_unmatched_unit_entrance_stays_unlinked_even_when_road_is_nearby():
    snapshot = _snapshot_case("Kivelän sairaala")
    snapshot["cases"][0]["inspected_entrances"] = snapshot["cases"][0]["inspected_entrances"][:1]
    citypack = _citypack(snapshot)
    report = _assess(snapshot, citypack)
    facility = report["cases"][0]
    entrance = facility["inspected_official_unit_entrances"][0]
    assert facility["facility_identity_status"] == "UNRESOLVED"
    assert entrance["facility_identity_status"] == "UNRESOLVED"
    assert entrance["candidate_directed_edges"][0]["distance_to_edge_m"] < 20
    assert entrance["road_access_status"] == "NOT_VERIFIED"
    assert entrance["directed_road_node_id"] is None


def test_mismatched_frozen_osm_or_facility_anchor_is_rejected():
    snapshot = _snapshot_case("Tölö gymnasium")
    citypack = _citypack(snapshot)
    wrong_source = citypack.sources[0].model_copy(update={"sha256": "c" * 64})
    with pytest.raises(ValueError, match="different frozen OSM"):
        _assess(snapshot, citypack.model_copy(update={"sources": (wrong_source,)}))
    moved_facility = citypack.facilities[0].model_copy(update={"lon": citypack.facilities[0].lon + 0.01})
    with pytest.raises(ValueError, match="anchor differs"):
        _assess(snapshot, citypack.model_copy(update={"facilities": (moved_facility,)}))


def test_saved_real_report_keeps_all_five_cases_and_seven_inspected_points_unverified():
    report = json.loads(REPORT.read_text())
    assert report["case_count"] == 5
    assert report["inspected_official_entrance_count"] == 7
    assert report["status"] == "CANDIDATES_ONLY_NOT_VERIFIED"
    assert report["network_temporality"] == "current_snapshot"
    assert report["distance_crs"] == "EPSG:3067"
    assert report["turn_coverage"] == "CITYPACK_CONNECTION_LIST_PRESENT"
    assert report["frozen_osm_geometry_review"] == "SOURCE_HASH_VERIFIED_CANDIDATES_ONLY"
    assert all(case["directed_road_node_id"] is None for case in report["cases"])
    entrances = [e for case in report["cases"] for e in case["inspected_official_unit_entrances"]]
    assert all(e["road_access_status"] == "NOT_VERIFIED" for e in entrances)
    assert all(len(e["candidate_directed_edges"]) == 5 for e in entrances)
    assert all(
        set(e["nearest_imported_vehicle_permitted_edges"]) == {"passenger", "emergency"} for e in entrances
    )

    aurora = next(case for case in report["cases"] if case["osm_name"] == "Auroran sairaala")
    assert aurora["facility_identity_status"] == "UNRESOLVED"
    entrance = aurora["inspected_official_unit_entrances"][0]
    assert entrance["official_entrance_id"] == 21577
    assert entrance["road_access_status"] == "NOT_VERIFIED"
    review = entrance["osm_source_context_review"]
    assert review["building_to_road_vehicle_access_status"] == "NOT_VERIFIED"
    assert review["official_unit_address_building_ref"] == "15"
    assert review["nearest_osm_building_ref"] == "14"
    assert [
        (building["osm_way_id"], building["name"], building["ref"])
        for building in review["osm_building_candidates"][:2]
    ] == [
        (26818356, "Aurora 14", "14"),
        (26818363, "Aurora 15", "15"),
    ]
    assert review["osm_building_candidates"][0]["distance_to_outline_m"] < 3
    assert 30 < review["osm_building_candidates"][1]["distance_to_outline_m"] < 33
    nearest_service = review["osm_service_way_candidates"][0]
    assert nearest_service["osm_way_id"] == 155739174
    assert nearest_service["access"] == "destination"
    assert nearest_service["distance_to_osm_line_m"] < 4
    directed = nearest_service["imported_directed_edges"]
    assert {edge["external_road_id"] for edge in directed} == {"155739174", "-155739174"}
    assert all("passenger" not in edge["imported_allowed_vehicle_classes"] for edge in directed)
    assert all("emergency" not in edge["imported_allowed_vehicle_classes"] for edge in directed)
    assert all(edge["turn_coverage"] == "CITYPACK_CONNECTION_LIST_PRESENT" for edge in directed)
    assert all(
        edge[key][vehicle] == 0
        for edge in directed
        for key in ("incoming_turn_counts", "outgoing_turn_counts")
        for vehicle in ("passenger", "emergency")
    )
    assert set(review["review_flags"]) == {
        "OFFICIAL_ADDRESS_NEAREST_OSM_BUILDING_REF_DISAGREES",
        "NEAREST_OSM_SERVICE_WAY_LACKS_IMPORTED_PASSENGER_AND_EMERGENCY_PERMISSION",
        "NEAREST_OSM_SERVICE_WAY_HAS_ZERO_IMPORTED_PASSENGER_AND_EMERGENCY_TURNS",
    }


def test_frozen_osm_geometry_review_is_hash_checked_and_stays_candidate(tmp_path):
    snapshot = _snapshot_case("Auroran sairaala")
    official = snapshot["cases"][0]["inspected_entrances"][0]["record"]
    lon, lat = float(official["longitude"]), float(official["latitude"])
    nodes = {
        1: (lon - 0.00002, lat - 0.00002),
        2: (lon + 0.00002, lat - 0.00002),
        3: (lon + 0.00002, lat + 0.00002),
        4: (lon - 0.00002, lat + 0.00002),
        5: (lon + 0.0005, lat - 0.00002),
        6: (lon + 0.00054, lat - 0.00002),
        7: (lon + 0.00054, lat + 0.00002),
        8: (lon + 0.0005, lat + 0.00002),
        9: (lon - 0.00003, lat - 0.00003),
        10: (lon + 0.00003, lat - 0.00003),
    }
    elements = [f'<node id="{id}" lon="{x}" lat="{y}" />' for id, (x, y) in nodes.items()]
    elements.extend(
        [
            (
                '<way id="26818356"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>'
                '<tag k="building" v="hospital"/><tag k="name" v="Aurora 14"/><tag k="ref" v="14"/></way>'
            ),
            (
                '<way id="26818363"><nd ref="5"/><nd ref="6"/><nd ref="7"/><nd ref="8"/><nd ref="5"/>'
                '<tag k="building" v="hospital"/><tag k="name" v="Aurora 15"/><tag k="ref" v="15"/></way>'
            ),
            (
                '<way id="155739174"><nd ref="9"/><nd ref="10"/>'
                '<tag k="highway" v="service"/><tag k="access" v="destination"/></way>'
            ),
        ]
    )
    osm_path = tmp_path / "frozen.osm"
    osm_path.write_text('<osm version="0.6" generator="test">' + "".join(elements) + "</osm>")
    snapshot["osm_source"]["sha256"] = hashlib.sha256(osm_path.read_bytes()).hexdigest()
    context = inspect_frozen_osm_context(snapshot, osm_path)
    assert [row["ref"] for row in context[21577]["osm_building_candidates"]] == ["14", "15"]
    assert context[21577]["osm_service_way_candidates"][0]["osm_way_id"] == 155739174
    with pytest.raises(ValueError, match="declared source SHA256"):
        inspect_frozen_osm_context({**snapshot, "osm_source": {"sha256": "f" * 64}}, osm_path)

    base = _citypack(snapshot).model_dump(mode="json")
    for edge, external in zip(base["edges"], ("155739174", "-155739174"), strict=True):
        edge["external_id"] = external
        edge["allowed_vehicle_classes"] = ["delivery", "bicycle", "pedestrian"]
    base["connections"][0]["allowed_vehicle_classes"] = ["pedestrian"]
    report = _assess(snapshot, CityPack.model_validate(base), osm_context=context)
    review = report["cases"][0]["inspected_official_unit_entrances"][0]["osm_source_context_review"]
    assert review["status"] == "CONFLICTING_SOURCE_CANDIDATE_NOT_VERIFIED"
    assert review["nearest_osm_building_ref"] == "14"
    assert {
        row["external_road_id"] for row in review["osm_service_way_candidates"][0]["imported_directed_edges"]
    } == {"155739174", "-155739174"}
    assert review["building_to_road_vehicle_access_status"] == "NOT_VERIFIED"


def test_cli_requires_explicit_local_citypack(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["service_map_road_candidates.py"])
    with pytest.raises(SystemExit) as error:
        service_map_road_candidates.main()
    assert error.value.code == 2
