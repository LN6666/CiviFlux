from __future__ import annotations

import hashlib
import json
from pathlib import Path

from experiments.oracle import labels

GROUPS = [
    "dual_corridor",
    "single_bridge",
    "isolated_zone",
    "reverse_direction",
    "transfer",
    "grade_separation",
    "time_boundary",
    "vehicle_class",
    "missing_data",
    "zero_disturbance",
    "candidate_noise",
    "multi_relation",
]


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def make_case(group: str, variant: int) -> dict:
    scale = 1 + variant * 0.25
    roads = [
        ("ab", "A", "B", 1),
        ("bc", "B", "C", 1),
        ("ad", "A", "D", 3),
        ("dc", "D", "C", 3),
        ("ch", "C", "H", 1),
        ("bd", "B", "D", 2),
    ]
    coords = {
        "A": [24.93, 60.17],
        "B": [24.94, 60.17],
        "C": [24.95, 60.17],
        "D": [24.94, 60.18],
        "H": [24.96, 60.17],
        "I": [24.96, 60.18],
        "X": [24.94, 60.17],
    }
    if group == "single_bridge":
        roads = [r for r in roads if r[0] not in {"ad", "dc", "bd"}]
    if group == "isolated_zone":
        roads = [r for r in roads if r[0] != "ch"]
    if group == "reverse_direction":
        roads = [(i, t, s, c) if i == "bc" else (i, s, t, c) for i, s, t, c in roads]
    if group == "transfer":
        roads += [("di", "D", "I", 2)]
    if group == "grade_separation":
        roads = [(i, "X" if i == "bc" else s, t, c) for i, s, t, c in roads]
    if group == "multi_relation":
        roads += [("ci", "C", "I", 2), ("ih", "I", "H", 3)]
    classes = ["passenger", "bus", "emergency"]
    city = {
        "schema_version": "1.0",
        "citypack_id": f"synthetic-{group}-{variant}",
        "timezone": "Europe/Helsinki",
        "network_temporality": "synthetic",
        "transit_temporality": "synthetic",
        "sources": [
            {
                "id": "SYNTHETIC-EVAL",
                "url": "local:synthetic-independent-oracle",
                "sha256": digest(roads),
                "retrieved_at": "2026-09-23T00:00:00Z",
                "license": "Apache-2.0",
            }
        ],
        "nodes": [{"id": i, "lon": p[0], "lat": p[1]} for i, p in sorted(coords.items())],
        "edges": [
            {
                "id": i,
                "source": s,
                "target": t,
                "length_m": cost * 100 * scale,
                "speed_kph": 36,
                "cost_s": cost * 10 * scale,
                "allowed_vehicle_classes": classes,
                "geometry": [coords[s], coords[t]],
                "source_id": "SYNTHETIC-EVAL",
                "external_id": i,
                "name": i,
                "access_evidence": "synthetic-explicit",
                "oneway": True,
            }
            for i, s, t, cost in roads
        ],
        "connections": [
            {"from_edge": a[0], "to_edge": b[0], "allowed_vehicle_classes": classes}
            for a in roads
            for b in roads
            if a[2] == b[1]
        ],
        "facilities": [],
        "transit": {
            "routes": [
                {
                    "id": "transit-verified",
                    "name": "Synthetic aligned route",
                    "source_id": "SYNTHETIC-EVAL",
                    "match_status": "verified" if group in {"transfer", "multi_relation"} else "candidate",
                    "edge_ids": ["ab", "bc"],
                }
            ]
        },
        "warnings": ["Synthetic engineering fixture; no historical or measured claims."],
    }
    for identity, node, kind in [
        ("hospital", "H", "Hospital"),
        ("fire_station", "D", "FireStation"),
        ("isolated_clinic", "I", "Facility"),
    ] + [(f"distractor-{i:02}", "A", "Facility") for i in range(20)]:
        city["facilities"].append(
            {
                "id": identity,
                "type": kind,
                "name": identity,
                "lon": coords[node][0],
                "lat": coords[node][1],
                "entrance_node_id": None if group == "missing_data" and identity == "hospital" else node,
                "source_id": "SYNTHETIC-EVAL",
                "external_id": identity,
                "snap_distance_m": None if group == "missing_data" and identity == "hospital" else 0,
                "access_status": "unknown"
                if group == "missing_data" and identity == "hospital"
                else "verified",
            }
        )
    if group == "candidate_noise":
        city["transit"]["routes"] += [
            {
                "id": f"candidate-route-{i}",
                "name": f"Unverified nearby shape{i}",
                "source_id": "SYNTHETIC-EVAL",
                "match_status": "candidate",
                "edge_ids": ["bc"],
            }
            for i in range(10)
        ]
    if group == "grade_separation":
        city["evidence"] = {
            "grade_separation": "B and X have identical coordinates but distinct topology; no intersection."
        }
    if group == "reverse_direction":
        city["connections"] = [c for c in city["connections"] if c["from_edge"] != "bc"]
    scenario = {
        "schema_version": "1.0",
        "scenario_id": f"eval-{group}-{variant}",
        "citypack_id": city["citypack_id"],
        "kind": "road",
        "timezone": "Europe/Helsinki",
        "analysis_at": "2026-05-16T10:00:00+03:00",
        "analysis_vehicle_class": "bus" if group == "vehicle_class" else "passenger",
        "window": {"start": "2026-05-16T09:00:00+03:00", "end": "2026-05-16T12:00:00+03:00"},
        "restrictions": []
        if group == "zero_disturbance"
        else [
            {
                "id": "closure",
                "edge_ids": ["bc"],
                "valid_from": "2026-05-16T09:00:00+03:00",
                "valid_to": "2026-05-16T10:00:00+03:00"
                if group == "time_boundary"
                else "2026-05-16T12:00:00+03:00",
                "blocked_classes": ["passenger"],
                "evidence_kind": "assumed",
                "evidence_refs": ["SYNTHETIC-EVAL"],
            }
        ],
        "incident": None,
        "assumptions": [
            {
                "id": "synthetic-assumption",
                "description": "Synthetic topology, costs and time-window closure; independent machine oracle labels held separately.",
                "affects": ["all"],
            }
        ],
        "objective": "facility_access",
        "engine": "routing",
        "ranking": "A2",
        "seed_spec": {"entity_ids": ["ab"], "same_for_pair": True},
    }
    return {
        "case_id": scenario["scenario_id"],
        "group": group,
        "variant": variant,
        "split": "train" if GROUPS.index(group) < 6 else "dev" if GROUPS.index(group) < 9 else "test",
        "city": city,
        "scenario": scenario,
    }


def freeze(root: Path) -> dict:
    target = root / "experiments/frozen"
    target.mkdir(parents=True, exist_ok=True)
    cases = [make_case(group, variant) for group in GROUPS for variant in range(4)]
    answer = {case["case_id"]: labels(case["city"], case["scenario"]) for case in cases}
    manifest = {
        "version": "1",
        "case_count": 48,
        "motif_count": 12,
        "variants_per_group": 4,
        "splits": {
            s: [g for g in GROUPS if next(c for c in cases if c["group"] == g)["split"] == s]
            for s in ["train", "dev", "test"]
        },
        "inputs_sha256": digest(cases),
        "labels_sha256": digest(answer),
        "label_method": "independent exhaustive edge-simple path enumeration; synthetic machine labels, not human labels",
        "setting": "post-analysis affected-facility retrieval. Shared routing facts may enter graph; no physical prediction claim.",
        "model_inputs_allowlist": ["objective", "relation semantic definitions"],
        "model_inputs_denylist": ["labels", "heldout outcomes", "city geometry", "facility observations"],
        "frozen_hyperparameters": {
            "alpha": 0.85,
            "epsilon": 0.1,
            "rank_key": "absolute delta_attention descending; object_id tie-break",
            "top_k": [10, 20],
            "sensitivity": "NOT_RUN; no test-tuned profile",
        },
        "claim_limitations": [
            "Only3 heldout motifs; descriptive grouped summaries, no significance/generalization claim.",
            "A0 physical facts provide direct affected-facility baseline in post-analysis setting.",
            "All data synthetic; real-city evidence audited separately.",
        ],
    }
    for name, data in [("cases.json", cases), ("labels.json", answer), ("manifest.json", manifest)]:
        path = target / name
        encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
        if path.exists() and path.read_text() != encoded:
            raise RuntimeError(
                "Frozen experiment differs; create new explicitly versioned dataset rather than overwrite labels"
            )
        path.write_text(encoded)
    return manifest
