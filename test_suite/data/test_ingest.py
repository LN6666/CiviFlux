import json
from datetime import date
from pathlib import Path
from zipfile import ZipFile

import pytest
from urbanimpact.citypack.fetch import fetch, sha256_file

from adapters.gtfs.reader import Feed, inspect_feed, parse_gtfs_time, service_ids_on
from adapters.osm.network import distance_m, stable_id


def test_gtfs_service_day_overnight_and_calendar_exceptions():
    assert parse_gtfs_time("25:12:05") == 90725
    for bad in ["12:60:00", "-1:00:00", "25:01", "12:01:60", "168:00:00"]:
        with pytest.raises(ValueError):
            parse_gtfs_time(bad)
    calendar = [
        dict(
            service_id="weekdays",
            start_date="20260101",
            end_date="20261231",
            monday="1",
            tuesday="1",
            wednesday="1",
            thursday="1",
            friday="1",
            saturday="0",
            sunday="0",
        )
    ]
    exceptions = [
        {"service_id": "weekdays", "date": "20260515", "exception_type": "2"},
        {"service_id": "special", "date": "20260515", "exception_type": "1"},
    ]
    assert service_ids_on(date(2026, 5, 15), calendar, exceptions) == {"special"}
    assert service_ids_on(date(2026, 5, 16), calendar, exceptions) == set()


def test_archive_traversal_and_duplicate_rejected(tmp_path):
    for names in [["../stops.txt"], ["stops.txt", "stops.txt"]]:
        path = tmp_path / "unsafe.zip"
        with ZipFile(path, "w") as out:
            for name in names:
                out.writestr(name, "dummy")
        with pytest.raises(ValueError):
            Feed(path)


def test_fetch_no_implicit_egress_and_frozen_hash(tmp_path):
    with pytest.raises(PermissionError):
        fetch("gtfs", tmp_path)
    with pytest.raises(ValueError):
        fetch("https://evil.test/a", tmp_path, allow_egress=True)
    path = tmp_path / "hsl.zip"
    path.write_bytes(b"old frozen bytes")
    meta = {"sha256": sha256_file(path), "status": "VERIFIED_BYTES"}
    path.with_suffix(".zip.source.json").write_text(json.dumps(meta))
    assert fetch("gtfs", tmp_path) == meta
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        fetch("gtfs", tmp_path)


def test_stable_ids_and_distance():
    assert stable_id("edge", "12#0") == stable_id("edge", "12#0")
    assert stable_id("edge", "12#0") != stable_id("edge", "12_0")
    assert 110 < distance_m([24, 60], [24, 60.001]) < 112


def test_gtfs_full_small_feed(tmp_path):
    tables = {
        "stops.txt": "stop_id,stop_name,stop_lon,stop_lat\ns,Station,24.94,60.18\n",
        "routes.txt": "route_id,route_type,route_short_name\nr,3,1\n",
        "trips.txt": "route_id,service_id,trip_id,shape_id,direction_id\nr,weekdays,t,shape,0\n",
        "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nt,25:00:00,25:01:00,s,1\n",
        "calendar_dates.txt": "service_id,date,exception_type\nweekdays,20260923,1\n",
        "shapes.txt": "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\nshape,60.18,24.94,1\nshape,60.19,24.95,2\n",
    }
    path = tmp_path / "valid.zip"
    with ZipFile(path, "w") as out:
        for name, text in tables.items():
            out.writestr(name, text)
    result = inspect_feed(path, [24.9, 60.1, 25, 60.2])
    assert result["coverage"]["times_over_24h"] == 2
    assert result["coverage"]["active_service_days"] == 1
    assert result["coverage"]["historical_case_dates"]["2026-05-15"] is False
    assert result["shape_match_status"].startswith("candidate")
    assert len(result["routes"]) == len(result["shapes"]) == len(result["stops"]) == 1


def test_real_citypack_sources_and_turns():
    root = Path(__file__).resolve().parents[2]
    path = root / "data/citypacks/helsinki-current/citypack.json"
    if not path.exists():
        pytest.skip("real citypack has not yet been built; release required")
    from urbanimpact.citypack import load_citypack

    city = load_citypack(path)
    assert city.network_temporality == "current_snapshot"
    assert len(city.edges) > 1000 and city.connections
    assert all(c.from_edge != c.to_edge for c in city.connections)
    assert len(city.transit["stops"]) > 10 and len(city.transit["routes"]) > 10
    for source in city.sources:
        assert sha256_file(root / source.path) == source.sha256
    assert not any(city.transit["coverage"]["historical_case_dates"].values())
    assert all(f.access_status != "verified" for f in city.facilities)


def test_osm_import_preserves_oneway_and_no_right_turn(tmp_path):
    from adapters.osm.network import convert_network, extract_roi

    root = Path(__file__).resolve().parents[2]
    source = tmp_path / "source.osm"
    source.write_text("""<osm version="0.6" generator="unit-test">
    <node id="1" lat="60.0000" lon="24.0000"/><node id="2" lat="60.0010" lon="24.0000"/><node id="3" lat="60.0020" lon="24.0000"/><node id="4" lat="60.0010" lon="24.0020"/>
    <way id="10"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/><tag k="name" v="South"/></way>
    <way id="20"><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/><tag k="name" v="North"/></way>
    <way id="30"><nd ref="2"/><nd ref="4"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/><tag k="name" v="East"/></way>
    <relation id="100"><member type="way" ref="10" role="from"/><member type="node" ref="2" role="via"/><member type="way" ref="30" role="to"/><tag k="type" v="restriction"/><tag k="restriction" v="no_right_turn"/></relation></osm>""")
    selected = extract_roi(source, tmp_path / "roi.osm", [23.99, 59.99, 24.01, 60.01])
    net = convert_network(
        tmp_path / "roi.osm", tmp_path / "net.xml", root / ".venv/bin/netconvert", tmp_path / "log", selected
    )
    roads = {e["name"]: e for e in net["edges"]}
    assert set(roads) == {"South", "North", "East"}
    assert selected["restriction_relations"] == 1
    turns = {(t["from_edge"], t["to_edge"]) for t in net["connections"]}
    assert (roads["South"]["id"], roads["North"]["id"]) in turns
    assert (roads["South"]["id"], roads["East"]["id"]) not in turns
    assert roads["South"]["geometry"][0][1] < roads["South"]["geometry"][-1][1]


def test_extended_gtfs_bus_type_is_candidate():
    from urbanimpact.citypack.build import shape_candidates

    edge = {"id": "e", "geometry": [[24.94, 60.18], [24.941, 60.181]], "allowed_vehicle_classes": ["bus"]}
    transit = {
        "routes": [{"route_id": "r", "route_type": "701"}],
        "shapes": [{"shape_id": "s", "route_ids": ["r"], "coordinates": edge["geometry"]}],
    }
    matches = shape_candidates(transit, [edge])
    assert matches[0]["candidate_edge_ids"] == ["e"]
    assert matches[0]["status"] == "candidate"


def test_evidence_cases_do_not_invent_hours_or_fire_perimeter():
    root = Path(__file__).resolve().parents[2]
    path = root / "evidence/wp1/case_review.json"
    if not path.exists():
        pytest.skip("case-review command required")
    report = json.loads(path.read_text())
    assert report["human_review_status"] == "PENDING"
    assert all(m["exact_start"] is None and m["exact_end"] is None for m in report["road_case"]["mapping"])
    assert report["fire_case"]["incident_facts"]["actual_cordon"] is None
    assert report["fire_case"]["incident_facts"]["building_coordinate"] is None
    assert report["fire_case"]["measured_prediction_validated"] is False
