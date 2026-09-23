"""Small explicit synthetic fixture shipped for offline engineering verification."""

from .contracts import CityPack, Scenario
from .util import digest


def toy_city() -> CityPack:
    coords = {
        "A": (24.93, 60.17),
        "B": (24.94, 60.17),
        "C": (24.95, 60.17),
        "D": (24.94, 60.18),
        "H": (24.96, 60.17),
    }
    roads = [
        ("ab", "A", "B", 1),
        ("bc", "B", "C", 1),
        ("ad", "A", "D", 3),
        ("dc", "D", "C", 3),
        ("ch", "C", "H", 1),
    ]
    classes = [
        "passenger",
        "bus",
        "emergency",
        "delivery",
        "truck",
        "bicycle",
        "pedestrian",
        "taxi",
        "motorcycle",
    ]
    return CityPack.model_validate(
        {
            "citypack_id": "TOY-DUAL-CORRIDOR",
            "network_temporality": "synthetic",
            "transit_temporality": "synthetic",
            "sources": [
                {
                    "id": "SYNTHETIC-TOY",
                    "url": "local:synthetic",
                    "sha256": digest(roads),
                    "retrieved_at": "2026-09-23T00:00:00Z",
                    "license": "Apache-2.0",
                }
            ],
            "nodes": [{"id": k, "lon": v[0], "lat": v[1]} for k, v in coords.items()],
            "edges": [
                {
                    "id": id,
                    "source": a,
                    "target": b,
                    "length_m": cost * 100,
                    "speed_kph": 360,
                    "cost_s": cost,
                    "allowed_vehicle_classes": classes,
                    "geometry": [coords[a], coords[b]],
                    "source_id": "SYNTHETIC-TOY",
                    "external_id": id,
                    "name": id,
                    "access_evidence": "synthetic explicit",
                }
                for id, a, b, cost in roads
            ],
            "connections": [
                {"from_edge": x[0], "to_edge": y[0], "allowed_vehicle_classes": classes}
                for x in roads
                for y in roads
                if x[2] == y[1]
            ],
            "facilities": [
                {
                    "id": "hospital",
                    "type": "Hospital",
                    "name": "Synthetic hospital",
                    "lon": coords["H"][0],
                    "lat": coords["H"][1],
                    "entrance_node_id": "H",
                    "source_id": "SYNTHETIC-TOY",
                    "external_id": "H",
                    "snap_distance_m": 0,
                    "access_status": "verified",
                }
            ],
            "transit": {
                "routes": [
                    {
                        "id": "bus_route",
                        "name": "Synthetic line",
                        "edge_ids": ["ab", "bc", "ch"],
                        "match_status": "verified",
                        "source_id": "SYNTHETIC-TOY",
                    }
                ]
            },
            "warnings": ["Synthetic test network; coordinates illustrative, not Helsinki roads."],
        }
    )


def toy_scenario(*, kind="road", ranking="A2", closed=("bc",)) -> Scenario:
    return Scenario.model_validate(
        {
            "scenario_id": "toy-" + kind,
            "citypack_id": "TOY-DUAL-CORRIDOR",
            "kind": kind,
            "analysis_at": "2026-05-16T10:00:00+03:00",
            "window": {"start": "2026-05-16T09:00:00+03:00", "end": "2026-05-16T12:00:00+03:00"},
            "restrictions": [
                {
                    "id": "r1",
                    "edge_ids": list(closed),
                    "valid_from": "2026-05-16T09:00:00+03:00",
                    "valid_to": "2026-05-16T12:00:00+03:00",
                    "blocked_classes": ["passenger"],
                    "evidence_kind": "assumed",
                    "evidence_refs": ["SYNTHETIC-TOY"],
                }
            ]
            if closed
            else [],
            "incident": {
                "source_refs": ["SYNTHETIC-TOY"],
                "location_text": "Synthetic incident",
                "geometry_ref": "toy:point",
                "geometry_status": "assumed",
                "point": [24.94, 60.17],
            }
            if kind == "fire"
            else None,
            "assumptions": [
                {
                    "id": "synthetic",
                    "description": "Synthetic geometry, cost and restriction; not operational guidance.",
                    "affects": ["all"],
                }
            ],
            "ranking": ranking,
            "seed_spec": {"entity_ids": ["bc"]},
        }
    )
