"""Evaluate a frozen Service Map snapshot without changing a CityPack.

An official building entrance is evidence about a service unit. It is not a
directed, vehicle-permitted road connection or a verified emergency route.
"""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import datetime
from urllib.parse import urlparse

from adapters.osm.network import stable_id

SERVICE_MAP = "City of Helsinki Service Map"
LICENSE = "CC-BY-4.0"
SOURCE_HOST = "www.hel.fi"
BASE_PATH = "/palvelukarttaws/rest/v4/"
GENERIC_OSM_NAMES = {"school", "hospital", "clinic", "fire_station"}
MAX_IDENTITY_DISTANCE_M = 100.0


def _utc_timestamp(value: str) -> None:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Source retrieval time must include a timezone")


def _source_url(value: str, resource: str) -> None:
    url = urlparse(value)
    if url.scheme != "https" or url.hostname != SOURCE_HOST or not url.path.startswith(BASE_PATH + resource):
        raise ValueError("Unexpected Service Map source URL")


def _hash(value: str) -> None:
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("Source response SHA256 is missing or malformed")


def _name(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").casefold().split())


def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(h)))


def _point(record: dict) -> tuple[float, float]:
    lon, lat = float(record["longitude"]), float(record["latitude"])
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError("Invalid source coordinates")
    return lon, lat


def assess_snapshot(snapshot: dict) -> dict:
    """Return identity evidence only; never assign a drivable road node.

    A match needs a non-generic, exact multilingual name, a unique official
    unit in the searched results, and a unit point within 100 m of the OSM
    facility anchor. The threshold is a conservative identity filter, not a
    physical access or entrance accuracy threshold.
    """
    if snapshot.get("schema_version") != "1.0":
        raise ValueError("Unsupported Service Map evidence schema")
    source = snapshot["source"]
    if source.get("name") != SERVICE_MAP or source.get("license") != LICENSE:
        raise ValueError("Service Map attribution or license missing")
    if source.get("attribution") != SERVICE_MAP:
        raise ValueError("Service Map attribution missing")
    _utc_timestamp(source["retrieved_at"])
    osm_source = snapshot["osm_source"]
    _hash(osm_source["sha256"])
    _utc_timestamp(osm_source["retrieved_at"])

    rows = []
    seen_facilities = set()
    for case in snapshot["cases"]:
        facility = case["osm_facility"]
        facility_id = facility["id"]
        external_id = facility["external_id"]
        if facility_id in seen_facilities:
            raise ValueError("Duplicate OSM facility")
        seen_facilities.add(facility_id)
        way_id = re.fullmatch(r"way/(\d+)", external_id)
        if way_id is None or facility_id != stable_id("facility-way", way_id.group(1)):
            raise ValueError("Facility ID does not match OSM way provenance")
        anchor = _point({"longitude": facility["longitude"], "latitude": facility["latitude"]})

        units = {}
        searches = case["unit_searches"]
        if not searches:
            raise ValueError("Missing official unit search")
        for search in searches:
            _source_url(search["url"], "unit/")
            _utc_timestamp(search["retrieved_at"])
            _hash(search["response_sha256"])
            if search["result_count"] != len(search["units"]):
                raise ValueError("Unit search result count does not match retained records")
            for unit in search["units"]:
                if unit["id"] in units and unit != units[unit["id"]]:
                    raise ValueError("Conflicting official unit records")
                _point(unit)
                units[unit["id"]] = unit

        entrances = {}
        for item in case["inspected_entrances"]:
            _source_url(item["url"], "entrance/")
            _utc_timestamp(item["retrieved_at"])
            _hash(item["response_sha256"])
            entry = item["record"]
            if item["url"].rstrip("/").split("/")[-1] != str(entry["id"]):
                raise ValueError("Entrance URL and ID disagree")
            if entry["unit_id"] not in units:
                raise ValueError("Entrance refers to an uninspected unit")
            if entry["id"] in entrances:
                raise ValueError("Duplicate entrance record")
            _point(entry)
            entrances[entry["id"]] = entry

        normalized = _name(facility["name"])
        exact = []
        if normalized not in GENERIC_OSM_NAMES:
            for unit in units.values():
                names = {_name(unit.get(field)) for field in ("name_fi", "name_sv", "name_en")}
                if normalized in names:
                    exact.append(unit)
        near = [u for u in exact if _distance_m(anchor, _point(u)) <= MAX_IDENTITY_DISTANCE_M]
        matched = near[0] if len(exact) == len(near) == 1 else None
        matched_entrances = sorted(
            (e for e in entrances.values() if matched is not None and e["unit_id"] == matched["id"]),
            key=lambda e: e["id"],
        )
        rows.append(
            {
                "facility_id": facility_id,
                "osm_external_id": external_id,
                "osm_name": facility["name"],
                "identity_status": "OFFICIAL_UNIT_MATCH_CANDIDATE" if matched else "UNRESOLVED",
                "identity_rule": "unique exact multilingual name and official unit point within 100 m; not human approval",
                "official_unit_id": matched["id"] if matched else None,
                "official_unit_name": matched["name_fi"] if matched else None,
                "official_unit_point_distance_m": round(_distance_m(anchor, _point(matched)), 2)
                if matched
                else None,
                "inspected_official_unit_ids": sorted(units),
                "exact_name_unit_ids": sorted(u["id"] for u in exact),
                "official_unit_entrances": [
                    {
                        "id": e["id"],
                        "is_main_entrance": e["is_main_entrance"] == "Y",
                        "longitude": float(e["longitude"]),
                        "latitude": float(e["latitude"]),
                        "geometry_role": "official service-unit entrance point; not a road connection",
                    }
                    for e in matched_entrances
                ],
                "road_access_status": "NOT_VERIFIED",
                "directed_road_node_id": None,
                "needs_human_review": True,
            }
        )

    return {
        "status": "PARTIAL_IDENTITY_EVIDENCE_ONLY",
        "claim_boundary": "Official service-unit identity and published entrance points; no confirmed directed-road or vehicle access, current-network only.",
        "source": source,
        "osm_source": osm_source,
        "g102_status": "PARTIAL",
        "g205_status": "PARTIAL",
        "case_count": len(rows),
        "cases": rows,
    }
