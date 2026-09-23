"""Independent checks for official identity evidence and the road-access boundary."""

import copy
import json
import sys
from pathlib import Path

import pytest

from adapters.servicemap import assess_snapshot
from scripts import service_map_entrances

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "evidence/wp1/service_map_entrance_source_snapshot.json"
REPORT = ROOT / "evidence/wp1/service_map_entrance_audit.json"


def frozen_snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text())


def test_five_facilities_have_source_backed_identity_evidence_only():
    report = assess_snapshot(frozen_snapshot())
    assert report == json.loads(REPORT.read_text())
    assert report["case_count"] == 5
    assert (report["g102_status"], report["g205_status"]) == ("PARTIAL", "PARTIAL")
    assert report["source"]["license"] == "CC-BY-4.0"
    assert report["source"]["attribution"] == "City of Helsinki Service Map"
    assert all(case["road_access_status"] == "NOT_VERIFIED" for case in report["cases"])
    assert all(
        case["directed_road_node_id"] is None and case["needs_human_review"] for case in report["cases"]
    )

    by_name = {case["osm_name"]: case for case in report["cases"]}
    tolo = by_name["Tölö gymnasium"]
    assert tolo["identity_status"] == "OFFICIAL_UNIT_MATCH_CANDIDATE"
    assert tolo["official_unit_id"] == 6820
    assert [e["id"] for e in tolo["official_unit_entrances"]] == [19489]
    assert tolo["official_unit_entrances"][0]["geometry_role"].endswith("not a road connection")
    assert all(
        case["identity_status"] == "UNRESOLVED" for name, case in by_name.items() if name != "Tölö gymnasium"
    )


def test_duplicate_exact_official_units_cannot_be_silently_resolved():
    snapshot = frozen_snapshot()
    case = next(c for c in snapshot["cases"] if c["osm_facility"]["name"] == "Tölö gymnasium")
    second = copy.deepcopy(next(u for u in case["unit_searches"][0]["units"] if u["id"] == 6820))
    second["id"] = 999999
    case["unit_searches"][0]["units"].append(second)
    case["unit_searches"][0]["result_count"] += 1
    result = assess_snapshot(snapshot)
    tolo = next(c for c in result["cases"] if c["osm_name"] == "Tölö gymnasium")
    assert tolo["identity_status"] == "UNRESOLVED"
    assert tolo["official_unit_id"] is None
    assert tolo["official_unit_entrances"] == []


def test_nearby_generic_amenity_and_far_exact_name_cannot_match():
    snapshot = frozen_snapshot()
    generic = snapshot["cases"][0]
    generic_unit = generic["unit_searches"][0]["units"][0]
    generic_unit["name_fi"] = "school"
    generic["unit_searches"][0]["units"] = [generic_unit]
    generic["unit_searches"][0]["result_count"] = 1
    school = snapshot["cases"][1]
    tolo = next(u for u in school["unit_searches"][0]["units"] if u["id"] == 6820)
    tolo["longitude"] = 25.5
    result = assess_snapshot(snapshot)
    assert result["cases"][0]["identity_status"] == "UNRESOLVED"
    assert result["cases"][1]["identity_status"] == "UNRESOLVED"


def test_untrusted_provenance_and_unlinked_entrance_are_rejected():
    snapshot = frozen_snapshot()
    snapshot["source"]["attribution"] = ""
    with pytest.raises(ValueError, match="attribution"):
        assess_snapshot(snapshot)
    snapshot = frozen_snapshot()
    snapshot["cases"][1]["unit_searches"][0]["url"] = "https://example.net/unit/"
    with pytest.raises(ValueError, match="source URL"):
        assess_snapshot(snapshot)
    snapshot = frozen_snapshot()
    snapshot["cases"][1]["inspected_entrances"][0]["record"]["unit_id"] = 999999
    with pytest.raises(ValueError, match="uninspected unit"):
        assess_snapshot(snapshot)


def test_official_building_entrance_never_sets_directed_road_access():
    snapshot = frozen_snapshot()
    case = snapshot["cases"][1]
    case["inspected_entrances"][0]["record"]["road_node_id"] = "osm:node:250385481:79c687a0"
    result = assess_snapshot(snapshot)
    tolo = result["cases"][1]
    assert tolo["official_unit_entrances"][0]["id"] == 19489
    assert tolo["directed_road_node_id"] is None
    assert tolo["road_access_status"] == "NOT_VERIFIED"


def test_refresh_requires_explicit_egress_before_any_request(monkeypatch):
    def forbidden_request(_url):
        raise AssertionError("Unexpected network request")

    monkeypatch.setattr(service_map_entrances, "_fetch", forbidden_request)
    monkeypatch.setattr(sys, "argv", ["service_map_entrances.py", "--refresh"])
    with pytest.raises(SystemExit) as error:
        service_map_entrances.main()
    assert error.value.code == 2
