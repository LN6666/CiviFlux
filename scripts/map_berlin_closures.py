#!/usr/bin/env python3
"""Create review candidates for two explicitly bounded Berlin 2026 closures.

The official notice is manually transcribed below. Name and coordinate matching
only proposes directed OSM edges; it does not establish exact signed closure
limits, exemptions, actual operation, or a validated traffic outcome.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from urbanimpact.citypack.fetch import sha256_file
from urbanimpact.contracts import CityPack, Restriction

NOTICE = ROOT / "data/raw/berlin-marathon-2026-official-closure.html"
NOTICE_SHA256 = "a83157701a57001f1d93e24fe0869fc7936a13264bef51357f715b8d9ee4abd9"
NOTICE_URL = "https://www.berlin.de/sen/uvk/presse/pressemitteilungen/2026/pressemitteilung.1716477.php"
CASES = (
    {
        "id": "berlin-2026-active-17-juni",
        "street": "Straße des 17. Juni",
        "official_extent": "between Großer Stern and Brandenburger Tor; Yitzhak-Rabin-Straße is also affected but not mapped here",
        "midpoint_bbox": [13.347, 52.512, 13.378, 52.518],
        "valid_from": "2026-09-21T06:00:00+02:00",
        "valid_to": "2026-09-26T18:00:00+02:00",
        "time_caveat": "This is only the prospective comparison horizon, NOT the official reopening time. The notice gives staged reopening on 29 Sep and 1 Oct; this subset has not been split and reviewed against those stages.",
        "prediction_role": "known-starting-state candidate, not a prospective forecast of its own onset",
    },
    {
        "id": "berlin-2026-upcoming-unter-den-linden",
        "street": "Unter den Linden",
        "official_extent": "between Pariser Platz and Friedrichstraße",
        "midpoint_bbox": [13.3795, 52.5155, 13.3893, 52.5180],
        "valid_from": "2026-09-26T07:00:00+02:00",
        "valid_to": "2026-09-26T18:00:00+02:00",
        "time_caveat": "Official planned Saturday hours; actual operation and vehicle exemptions still need independent verification.",
        "prediction_role": "prospective incremental closure candidate if prediction is frozen before 26 Sep 07:00 Berlin time",
    },
)


def map_candidates(root: Path = ROOT) -> dict:
    notice = root / NOTICE.relative_to(ROOT)
    if sha256_file(notice) != NOTICE_SHA256:
        raise ValueError("official notice changed; preserve and review a new version")
    pack_path = root / "data/citypacks/berlin-marathon-2026/citypack.json"
    city = CityPack.model_validate_json(pack_path.read_bytes())
    mapped = []
    for case in CASES:
        xmin, ymin, xmax, ymax = case["midpoint_bbox"]
        matches = []
        for edge in city.edges:
            if edge.name != case["street"] or "passenger" not in edge.allowed_vehicle_classes or not edge.geometry:
                continue
            lon = sum(point[0] for point in edge.geometry) / len(edge.geometry)
            lat = sum(point[1] for point in edge.geometry) / len(edge.geometry)
            if xmin <= lon <= xmax and ymin <= lat <= ymax:
                matches.append(edge.id)
        matches.sort()
        if not matches:
            raise ValueError(f"no candidate directed edges for {case['id']}")
        # Contract validation checks identity, time order, and nonempty edge set.
        restriction = Restriction.model_validate(
            {
                "id": case["id"],
                "edge_ids": matches,
                "valid_from": case["valid_from"],
                "valid_to": case["valid_to"],
                "blocked_classes": ["passenger"],
                "evidence_kind": "announced",
                "evidence_refs": ["DE-BE-NOTICE-20260921"],
            }
        )
        mapped.append(
            {
                **case,
                "mapping_status": "CANDIDATE_UNREVIEWED",
                "mapping_method": "exact OSM street name, passenger-allowed directed edge, geometry mean within declared bbox",
                "candidate_directed_edge_ids": matches,
                "candidate_count": len(matches),
                "candidate_restriction": restriction.model_dump(mode="json"),
                "caveat": "The bbox is an analyst mapping aid, not an official closure polygon; inspect endpoints, direction, side carriageways and signed exceptions before simulation claims.",
            }
        )
    return {
        "status": "CANDIDATE_UNREVIEWED",
        "ontology_type": "RoadRestriction",
        "source_type": "EvidenceSource",
        "source_id": "DE-BE-NOTICE-20260921",
        "official_url": NOTICE_URL,
        "official_publication_date": "2026-09-21",
        "notice_sha256": NOTICE_SHA256,
        "citypack_id": city.citypack_id,
        "citypack_sha256": sha256_file(pack_path),
        "mapping_source": "manual transcription of two explicitly bounded notices; algorithmic road-edge proposal",
        "cases": mapped,
        "claim_ceiling": "announced restriction to directed-road candidate mapping; neither observed operation nor event-impact validation",
    }


if __name__ == "__main__":
    result = map_candidates()
    target = ROOT / "data/event_cases/berlin-marathon-2026-closure-candidates.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "counts": [c["candidate_count"] for c in result["cases"]], "path": str(target)}, indent=2))
