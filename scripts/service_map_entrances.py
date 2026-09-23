"""Freeze and check five Helsinki Service Map facility/entrance evidence cases.

Offline checking is the default. Refreshing fixed, public URLs requires an
explicit egress flag and never invokes a model or changes the CityPack.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from urbanimpact.util import atomic_json

from adapters.servicemap import assess_snapshot

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "evidence/wp1/service_map_entrance_source_snapshot.json"
REPORT = ROOT / "evidence/wp1/service_map_entrance_audit.json"
BASE = "https://www.hel.fi/palvelukarttaws/rest/v4"
MAX_RESPONSE_BYTES = 250_000
OSM_SOURCE = {
    "url": "https://karttapalvelu.storage.hsldev.com/hsl.osm/hsl.osm.pbf",
    "sha256": "07489394d83e34003a64f3aabc0b05669b6345bc3d02fbc550fc851c9f123c6d",
    "retrieved_at": "2026-09-23T14:45:49.389671+00:00",
    "license": "ODbL-1.0, © OpenStreetMap contributors; distributed by HSL",
}

# The source way anchors are already frozen candidate geometry in the initial
# Helsinki CityPack. Entrance IDs are inspected official records, not proposed
# OSM road-node replacements. One facility can have several official units.
SCOPE = (
    {
        "facility": (
            "osm:facility-way:1076884314:9d04b1e0",
            "way/1076884314",
            "school",
            24.981927992307696,
            60.17634510769231,
        ),
        "searches": ({"lon": "24.98192799", "lat": "60.17634511", "distance": "300"},),
        "entrance_ids": (),
    },
    {
        "facility": (
            "osm:facility-way:1100772558:880fe8fc",
            "way/1100772558",
            "Tölö gymnasium",
            24.9215624375,
            60.17924695,
        ),
        "searches": ({"search": "Tölö gymnasium"},),
        "entrance_ids": (19489,),
    },
    {
        "facility": (
            "osm:facility-way:33538166:a29160b4",
            "way/33538166",
            "Kivelän sairaala",
            24.918474381249997,
            60.17912127708333,
        ),
        "searches": ({"search": "Kivelän sairaala"}, {"search": "Kivelä"}),
        "entrance_ids": (19697, 639, 635, 20437),
    },
    {
        "facility": (
            "osm:facility-way:33323000:5f5a6080",
            "way/33323000",
            "Auroran sairaala",
            24.92576947368421,
            60.19346878070176,
        ),
        "searches": ({"search": "Auroran sairaala"},),
        "entrance_ids": (21577,),
    },
    {
        "facility": (
            "osm:facility-way:39343294:adb9dc53",
            "way/39343294",
            "Stadin ammattiopisto, Sturenkadun toimipaikka",
            24.953253010526314,
            60.19368714210526,
        ),
        "searches": ({"search": "Stadin ammattiopisto Sturenkadun"}, {"search": "Sturenkatu"}),
        "entrance_ids": (22849,),
    },
)


def _fetch(url: str) -> tuple[object, str, str]:
    request = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "CiviFlux-source-audit/1.0"}
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        final = urllib.parse.urlparse(response.url)
        if final.scheme != "https" or final.hostname != "www.hel.fi":
            raise ValueError("Service Map request redirected away from official host")
        if "json" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("Unexpected Service Map content type")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Service Map response exceeds byte limit")
    return json.loads(raw), hashlib.sha256(raw).hexdigest(), datetime.now(UTC).isoformat(timespec="seconds")


def _unit(record: dict) -> dict:
    return {
        "id": record["id"],
        "name_fi": record.get("name_fi"),
        "name_sv": record.get("name_sv"),
        "name_en": record.get("name_en"),
        "longitude": record["longitude"],
        "latitude": record["latitude"],
        "street_address_fi": record.get("street_address_fi"),
        "manual_coordinates": record.get("manual_coordinates"),
        "modified_time": record.get("modified_time"),
    }


def _entrance(record: dict) -> dict:
    return {
        "id": record["id"],
        "unit_id": record["unit_id"],
        "is_main_entrance": record.get("is_main_entrance"),
        "longitude": record["longitude"],
        "latitude": record["latitude"],
    }


def refresh() -> dict:
    """Fetch only fixed unit searches and seven exact entrance IDs, once each."""
    cases = []
    for item in SCOPE:
        facility_id, external_id, name, longitude, latitude = item["facility"]
        searches = []
        for params in item["searches"]:
            url = BASE + "/unit/?" + urllib.parse.urlencode(params)
            records, sha, retrieved_at = _fetch(url)
            if not isinstance(records, list):
                raise TypeError("Expected an official unit result list")
            searches.append(
                {
                    "url": url,
                    "response_sha256": sha,
                    "retrieved_at": retrieved_at,
                    "result_count": len(records),
                    "units": [_unit(record) for record in records],
                }
            )
        entrances = []
        for entrance_id in item["entrance_ids"]:
            url = f"{BASE}/entrance/{entrance_id}"
            record, sha, retrieved_at = _fetch(url)
            if not isinstance(record, dict) or record.get("id") != entrance_id:
                raise ValueError("Unexpected official entrance response")
            entrances.append(
                {
                    "url": url,
                    "response_sha256": sha,
                    "retrieved_at": retrieved_at,
                    "record": _entrance(record),
                }
            )
        cases.append(
            {
                "osm_facility": {
                    "id": facility_id,
                    "external_id": external_id,
                    "name": name,
                    "longitude": longitude,
                    "latitude": latitude,
                    "source_id": "S03-OSM",
                },
                "unit_searches": searches,
                "inspected_entrances": entrances,
            }
        )
    snapshot = {
        "schema_version": "1.0",
        "source": {
            "name": "City of Helsinki Service Map",
            "license": "CC-BY-4.0",
            "attribution": "City of Helsinki Service Map",
            "terms_url": "https://www.hel.fi/palvelukarttaws/restpages/index_en.html",
            "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "scope": "Five previously identified Helsinki OSM facility way anchors; selected official entrance IDs, not a complete entrance inventory",
        },
        "osm_source": OSM_SOURCE,
        "cases": cases,
    }
    assess_snapshot(snapshot)
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch the fixed public Service Map records")
    parser.add_argument("--allow-egress", action="store_true", help="Required with --refresh")
    args = parser.parse_args()
    if args.allow_egress != args.refresh:
        parser.error("--refresh and --allow-egress must be supplied together")
    if args.refresh:
        snapshot = refresh()
        report = assess_snapshot(snapshot)
        atomic_json(SNAPSHOT, snapshot)
        atomic_json(REPORT, report)
    else:
        snapshot = json.loads(SNAPSHOT.read_text())
        report = assess_snapshot(snapshot)
        if report != json.loads(REPORT.read_text()):
            raise ValueError("Saved Service Map audit differs from frozen source snapshot")
    print(json.dumps({"status": report["status"], "case_count": report["case_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
