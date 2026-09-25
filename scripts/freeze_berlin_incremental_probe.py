#!/usr/bin/env python3
"""Freeze a bounded, conditional Berlin routing probe before a planned closure.

This deliberately compares two declared closure sets on the same current road
snapshot. It is not an observation of traffic, a verified closure map, or a
calibrated demand forecast.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from urbanimpact.citypack.fetch import sha256_file
from urbanimpact.contracts import CityPack
from urbanimpact.network import Router

CITY = ROOT / "data/citypacks/berlin-marathon-2026/citypack.json"
CASES = ROOT / "data/event_cases/berlin-marathon-2026-closure-candidates.json"
OUTPUT = ROOT / "evidence/events/berlin-2026-incremental-pre-onset-probe.json"
CUTOFF = datetime.fromisoformat("2026-09-26T07:00:00+02:00")

# Geographic waypoints are declared in source, before any model result is read.
# They identify synthetic OD pairs, not measured trip demand.
OD_COORDINATES = (
    ("west_to_east", (13.3800, 52.5162), (13.3920, 52.5176)),
    ("east_to_west", (13.3920, 52.5176), (13.3800, 52.5162)),
    ("north_south_control", (13.4070, 52.5320), (13.4070, 52.5260)),
)


def _nearest(nodes, lon: float, lat: float):
    # Latitude-adjusted squared degrees are sufficient for nearest-node
    # selection within this narrow urban bounding box.
    return min(
        nodes,
        key=lambda n: ((n.lon - lon) * 0.61) ** 2 + (n.lat - lat) ** 2,
    ).id


def freeze(root: Path = ROOT, now: datetime | None = None) -> dict:
    observed_at = now or datetime.now(timezone.utc)
    if observed_at >= CUTOFF:
        raise ValueError("pre-onset freeze window has closed; run as replay instead")
    city_path = root / CITY.relative_to(ROOT)
    cases_path = root / CASES.relative_to(ROOT)
    city_sha = sha256_file(city_path)
    cases_sha = sha256_file(cases_path)
    city = CityPack.model_validate_json(city_path.read_bytes())
    mapping = json.loads(cases_path.read_text())
    if mapping["citypack_sha256"] != city_sha or mapping["citypack_id"] != city.citypack_id:
        raise ValueError("closure candidates do not match frozen city snapshot")
    candidates = {case["id"]: case for case in mapping["cases"]}
    active = candidates["berlin-2026-active-17-juni"]
    upcoming = candidates["berlin-2026-upcoming-unter-den-linden"]
    if active["mapping_status"] != upcoming["mapping_status"] != "CANDIDATE_UNREVIEWED":
        raise ValueError("unexpected mapping status")
    active_blocked = frozenset(active["candidate_directed_edge_ids"])
    upcoming_blocked = frozenset(upcoming["candidate_directed_edge_ids"])
    passenger_sources = {e.source for e in city.edges if "passenger" in e.allowed_vehicle_classes}
    passenger_targets = {e.target for e in city.edges if "passenger" in e.allowed_vehicle_classes}
    usable = [n for n in city.nodes if n.id in passenger_sources & passenger_targets]
    index = Router._index(city, "passenger")
    routes = []
    for label, start, end in OD_COORDINATES:
        origin = _nearest(usable, *start)
        target = _nearest(usable, *end)
        baseline = Router._search(index, origin, [target], active_blocked)[target]
        incremental = Router._search(index, origin, [target], active_blocked | upcoming_blocked)[target]
        routes.append(
            {
                "label": label,
                "origin_coordinate": start,
                "target_coordinate": end,
                "origin_node": origin,
                "target_node": target,
                "known_active_candidate_arm": baseline,
                "active_plus_upcoming_candidate_arm": incremental,
                "delta_freeflow_route_time_s": (
                    incremental["travel_time_s"] - baseline["travel_time_s"]
                    if baseline["travel_time_s"] is not None and incremental["travel_time_s"] is not None
                    else None
                ),
            }
        )
    result = {
        "status": "FROZEN_PRE_ONSET_CONDITIONAL_PROBE",
        "frozen_at_utc": observed_at.astimezone(timezone.utc).isoformat(),
        "announced_upcoming_start": CUTOFF.isoformat(),
        "citypack_id": city.citypack_id,
        "citypack_sha256": city_sha,
        "closure_candidates_sha256": cases_sha,
        "notice_sha256": mapping["notice_sha256"],
        "source_code_sha256": sha256_file(root / "scripts/freeze_berlin_incremental_probe.py"),
        "od_spec_sha256": hashlib.sha256(json.dumps(OD_COORDINATES).encode()).hexdigest(),
        "method": "same directed current OSM/SUMO network, static free-flow edge costs and explicit turns; candidate active restrictions in both arms; candidate future restriction only in second arm",
        "vehicle_class": "passenger",
        "known_active_candidate_count": len(active_blocked),
        "upcoming_candidate_count": len(upcoming_blocked),
        "routes": routes,
        "claim_ceiling": "pre-onset conditional sensitivity on unreviewed candidate closures, not actual traffic prediction or V2/V3 validation",
        "limitations": [
            "The known starting state is partial; other announced closures are not mapped.",
            "Candidate edge selection has no independent directed-road review.",
            "No measured demand, congestion, actual closure operation, event-hour outcomes, or unaffected matched controls are present.",
            "Current network crop excludes diversion alternatives outside its boundary.",
        ],
    }
    output = root / OUTPUT.relative_to(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError("frozen probe already exists; never overwrite it")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


if __name__ == "__main__":
    result = freeze()
    print(json.dumps({"status": result["status"], "frozen_at_utc": result["frozen_at_utc"], "routes": len(result["routes"])}))
