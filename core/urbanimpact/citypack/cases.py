"""Evidence-labelled road and fire case material, never historical truth by default."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path

from adapters.osm.network import distance_m
from urbanimpact.citypack.fetch import sha256_file

OPERA = {
    "source_id": "S03-OSM",
    "external_id": "way/124699859",
    "name": "Suomen Kansallisooppera ja -baletti",
    "lon": 24.92966223934426,
    "lat": 60.18152144098361,
    "geometry_method": "mean of OSM way vertices; approximate landmark anchor, not entrance",
}

# These source fields define the geometry-selection recipe below. A changed
# announcement card needs an explicit new mapping review, not a silent reuse of
# candidate edges selected for the old wording.
ROAD_MAPPING_SOURCE_CONTRACT = {
    "R1": {
        "road_name": "Mannerheimintie",
        "direction": "southbound",
        "from_landmark": "Finnish National Opera and Ballet",
        "to_landmark": "Pohjoinen rautatiekatu",
    },
    "R2": {
        "road_name": "Helsinginkatu",
        "direction": None,
        "from_landmark": "Mannerheimintie",
        "to_landmark": "Sturenkatu",
    },
    "R3": {"road_name": "Mäntymäentie", "direction": None},
}


def _validated_road_notice(path: Path) -> tuple[dict, dict[str, dict], dict]:
    case = json.loads(path.read_text())
    if (
        case.get("case_id") != "HEL-CITYRUN-20260515-16"
        or case.get("source_ids") != ["S01"]
        or case.get("timezone") != "Europe/Helsinki"
        or case.get("event_dates") != ["2026-05-15", "2026-05-16"]
    ):
        raise ValueError("R1 source card does not match the frozen case mapping")
    facts = case.get("facts")
    if not isinstance(facts, list) or any(not isinstance(f, dict) or not f.get("fact_id") for f in facts):
        raise ValueError("R1 source card facts are invalid")
    by_id = {fact["fact_id"]: fact for fact in facts}
    if len(by_id) != len(facts) or set(by_id) != set(ROAD_MAPPING_SOURCE_CONTRACT) | {"R4"}:
        raise ValueError("R1 source facts and candidate mapping IDs differ")
    road_fact_ids = {fact_id for fact_id, fact in by_id.items() if "road_name" in fact}
    if road_fact_ids != set(ROAD_MAPPING_SOURCE_CONTRACT):
        raise ValueError("R1 source motor-road facts and mapping recipe differ")
    for fact_id, expected in ROAD_MAPPING_SOURCE_CONTRACT.items():
        fact = by_id[fact_id]
        if any(fact.get(field) != value for field, value in expected.items()):
            raise ValueError(f"{fact_id} source endpoints, road, or direction differ from mapping recipe")
        if "exact_start" not in fact or "exact_end" not in fact:
            raise ValueError(f"{fact_id} source time fields are missing")
        if (
            fact.get("evidence_kind") != "announced"
            or fact.get("exact_start") is not None
            or fact.get("exact_end") is not None
        ):
            raise ValueError(f"{fact_id} source time or evidence changed; mapping needs review")
    if by_id["R3"].get("announced_date_range") != case["event_dates"]:
        raise ValueError("R3 announced date range differs from the mapping scenario")
    if any("announced_date_range" in by_id[fact_id] for fact_id in ("R1", "R2")):
        raise ValueError("R1/R2 source date precision changed; mapping needs review")
    if any(field in by_id["R3"] for field in ("from_landmark", "to_landmark")):
        raise ValueError("R3 source endpoints changed; mapping needs review")
    baana = by_id["R4"]
    if (
        baana.get("feature_name") != "Baana"
        or baana.get("mode_scope") != ["walking", "cycling"]
        or "road_name" in baana
    ):
        raise ValueError("Baana source scope changed; review the motor-road separation")
    if not isinstance(baana.get("times_local"), list) or not baana["times_local"]:
        raise ValueError("Baana source intervals are missing")
    return case, by_id, baana


def _source_road_fact(case: dict, fact: dict) -> dict:
    date_range = fact.get("announced_date_range")
    return {
        "source_id": case["source_ids"][0],
        "road_name": fact["road_name"],
        "direction": fact.get("direction"),
        "from_landmark": fact.get("from_landmark"),
        "to_landmark": fact.get("to_landmark"),
        "event_dates_context": case["event_dates"],
        "announced_date_range": date_range,
        "time_precision": "date_range_only" if date_range else "event_dates_context_only",
        "exact_start": fact["exact_start"],
        "exact_end": fact["exact_end"],
        "evidence_kind": fact["evidence_kind"],
    }


def _named(edges, name):
    return [
        e
        for e in edges
        if e["name"].casefold() == name.casefold() and "passenger" in e["allowed_vehicle_classes"]
    ]


def _road_anchor(edges, point, nodes):
    ids = {e["source"] for e in edges} | {e["target"] for e in edges}
    return min((nodes[i] for i in ids), key=lambda n: distance_m(point, [n["lon"], n["lat"]]))


def _intersection(a, b, nodes):
    first = {e["source"] for e in a} | {e["target"] for e in a}
    second = {e["source"] for e in b} | {e["target"] for e in b}
    shared = sorted(first & second)
    if shared:
        # All alternatives preserved for review, not collapsed into false certainty.
        return [nodes[i] for i in shared]
    pairs = [
        (distance_m([nodes[i]["lon"], nodes[i]["lat"]], [nodes[j]["lon"], nodes[j]["lat"]]), i, j)
        for i in first
        for j in second
    ]
    _, i, j = min(pairs)
    return [nodes[i], nodes[j]]


def _snapshot(pack, kind, edge_ids, assumptions, incident=None):
    day = "2026-05-16" if kind == "road" else "2026-05-23"
    start = day + ("T09:00:00Z" if kind == "road" else "T17:55:00Z")
    end = day + ("T10:00:00Z" if kind == "road" else "T18:55:00Z")
    return {
        "schema_version": "1.0",
        "scenario_id": "helsinki-" + kind + "-current-network-whatif",
        "citypack_id": pack["citypack_id"],
        "kind": kind,
        "timezone": "Europe/Helsinki",
        "analysis_at": start,
        "window": {"start": start, "end": end},
        "restrictions": [
            {
                "id": "example-" + kind + "-assumed-closure",
                "edge_ids": edge_ids,
                "valid_from": start,
                "valid_to": end,
                "blocked_classes": ["passenger", "bus", "delivery", "truck", "taxi", "motorcycle"],
                "evidence_kind": "assumed",
                "evidence_refs": ["R1-assumptions" if kind == "road" else "F1-assumptions"],
            }
        ],
        "incident": incident,
        "assumptions": assumptions,
        "objective": "facility_access",
        "engine": "routing",
        "ranking": "A2",
        "seed_spec": {"entity_ids": [edge_ids[0]], "same_for_pair": True},
    }


def _review_map(path: Path, edges: list[dict], groups: list[dict], anchors: list[dict]):
    """GIS/web-first review artifact; scientific-figure-making excludes this format."""
    from pyproj import Transformer

    convert = Transformer.from_crs(4326, 3067, always_xy=True).transform
    selected = {eid: group for group in groups for eid in group["directed_edge_ids"]}
    roads = [
        e
        for e in edges
        if e["id"] in selected
        or e["name"].casefold()
        in {
            "mannerheimintie",
            "helsinginkatu",
            "sturenkatu",
            "mäntymäentie",
            "pohjoinen rautatiekatu",
            "leonkatu",
        }
    ]
    all_points = [convert(*p) for e in roads for p in e["geometry"]]
    minx, miny = min(p[0] for p in all_points), min(p[1] for p in all_points)
    maxx, maxy = max(p[0] for p in all_points), max(p[1] for p in all_points)
    scale = min(1060 / (maxx - minx), 780 / (maxy - miny))

    def pt(lon, lat):
        x, y = convert(lon, lat)
        return 30 + (x - minx) * scale, 820 - (y - miny) * scale

    content = []
    colors = {"R1": "#c34435", "R2": "#a96714", "R3": "#74399b", "F1": "#006a85"}
    for e in roads:
        points = [pt(*p) for p in e["geometry"]]
        d = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in points)
        group = selected.get(e["id"])
        color = colors[group["fact_id"]] if group else "#b8c2cd"
        title = html.escape(e["name"] + " | " + e["id"] + " | " + (group["fact_id"] if group else "context"))
        content.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{2.5 if group else 0.8}" marker-end="url(#arrow)" ><title>{title}</title></path>'
        )
    anchor_groups = []
    for a in anchors:
        group = next(
            (g for g in anchor_groups if distance_m([a["lon"], a["lat"]], [g[0]["lon"], g[0]["lat"]]) < 80),
            None,
        )
        if group is None:
            anchor_groups.append([a])
        else:
            group.append(a)
    legend = []
    for i, group in enumerate(anchor_groups, 1):
        a = group[0]
        x, y = pt(a["lon"], a["lat"])
        label = html.escape(" / ".join(sorted({g.get("name", g.get("id", "anchor")) for g in group})))
        content.append(
            f'<g><title>{label}</title><circle cx="{x:.2f}" cy="{y:.2f}" r="7" fill="#112233"/><text x="{x:.2f}" y="{y + 4:.2f}" text-anchor="middle" font-size="9" fill="white">{i}</text></g>'
        )
        legend.append(f"<li>{label} ({a['lon']:.6f}, {a['lat']:.6f}); {len(group)} candidate anchors</li>")
    path.write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Helsinki directed-edge review</title><style>body{font:16px system-ui;background:#f7f8fa;margin:24px;color:#17212b}svg{background:white;max-width:100%;border:1px solid #ccd3dc}p{max-width:1100px}a{color:#006a85}</style><h1>Helsinki directed-edge review</h1><p>Current OSM network. Machine-selected candidates, awaiting independent human review. Red: Mannerheimintie southbound; amber: Helsinginkatu; violet: Mäntymäentie; teal: Leonkatu illustrative assumption. Arrows show network travel direction; hover for exact edge ID. Case hours and vehicle exemptions are unknown. Fire geometry is street-level uncertainty, with no certified perimeter.</p><p><a href="directed_road_mapping.csv">Mapping CSV</a> · <a href="case_review.json">Evidence card</a> · <a href="case_geometry.geojson">GIS geometry</a></p><svg viewBox="0 0 1120 870" role="img" aria-label="Directed candidate road segments and source landmark anchors"><defs><marker id="arrow" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L5,2.5 L0,5" fill="#4b5563"/></marker></defs>'
        + "".join(content)
        + "</svg><ol>"
        + "".join(legend)
        + "</ol><p>Data: © OpenStreetMap contributors, ODbL; imported via HSL. EPSG:3067 display projection. No external tiles or telemetry.</p></html>"
    )


def review(root: Path) -> dict:
    from urbanimpact.contracts import Scenario

    source_card_path = root / "cases/helsinki_cityrun_2026/case_evidence.json"
    source_case, source_facts, baana = _validated_road_notice(source_card_path)
    source_card_sha256 = sha256_file(source_card_path)
    out = root / "evidence/wp1"
    out.mkdir(parents=True, exist_ok=True)
    pack_path = root / "data/citypacks/helsinki-current/citypack.json"
    pack = json.loads(pack_path.read_text())
    edges = pack["edges"]
    nodes = {n["id"]: n for n in pack["nodes"]}
    manner = _named(edges, source_facts["R1"]["road_name"])
    northrail = _named(edges, source_facts["R1"]["to_landmark"])
    helsing = _named(edges, source_facts["R2"]["road_name"])
    sturen = _named(edges, source_facts["R2"]["to_landmark"])
    opera_anchor = _road_anchor(manner, [OPERA["lon"], OPERA["lat"]], nodes)
    south_anchors = _intersection(manner, northrail, nodes)
    lower_lat = min(a["lat"] for a in south_anchors)
    r1 = [
        e
        for e in manner
        if e["geometry"][0][1] > e["geometry"][-1][1]
        and lower_lat <= sum(p[1] for p in e["geometry"]) / len(e["geometry"]) <= opera_anchor["lat"]
    ]
    west = _intersection(helsing, manner, nodes)
    east = _intersection(helsing, sturen, nodes)
    west_lon = min(a["lon"] for a in west)
    east_lon = max(a["lon"] for a in east)
    r2 = [e for e in helsing if west_lon <= sum(p[0] for p in e["geometry"]) / len(e["geometry"]) <= east_lon]
    r3 = _named(edges, source_facts["R3"]["road_name"])
    leon = _named(edges, "Leonkatu")
    if not all([r1, r2, r3, leon]):
        raise ValueError("named road mapping incomplete")
    # Only one explicit example edge is assumed blocked; no inferred radius or perimeter.
    fire_edge = max(leon, key=lambda e: e["length_m"])
    groups = []
    for fact, chosen, direction in [
        ("R1", r1, "southbound"),
        ("R2", r2, "both directions assumed"),
        ("R3", r3, "both directions assumed"),
        ("F1", [fire_edge], "illustrative directed edge assumption"),
    ]:
        group = {
            "fact_id": fact,
            "directed_edge_ids": sorted(e["id"] for e in chosen),
            "direction": direction,
            "review_status": "MACHINE_CANDIDATE_REQUIRES_HUMAN_REVIEW",
            "reviewed_by": "Codex data worker; not an independent human expert",
            "review_method": "OSM name + landmark/intersection geometric bounds + directed centerline orientation",
            "exact_start": None,
            "exact_end": None,
            "vehicle_exemptions": None,
        }
        if fact in ROAD_MAPPING_SOURCE_CONTRACT:
            group["source_fact"] = _source_road_fact(source_case, source_facts[fact])
            group["source_card_sha256"] = source_card_sha256
        groups.append(group)
    if {g["fact_id"] for g in groups[:3]} != set(ROAD_MAPPING_SOURCE_CONTRACT):
        raise ValueError("R1 candidate groups and source fact IDs differ")
    road_assumptions = [
        {
            "id": "R1-assumptions",
            "description": "Illustrative what-if: all machine-mapped announced roads are simultaneously restricted 12:00–13:00 Europe/Helsinki on16 May. Exact hours and exemptions are unknown; both directions on Helsinginkatu and Mäntymäentie are assumed. Current September network/schedule replaces unavailable historical data. Not a minute-by-minute historical replay.",
            "affects": [
                "restriction_window",
                "road_mapping",
                "vehicle_permissions",
                "network_temporality",
                "transit_temporality",
            ],
        }
    ]
    fire_assumptions = [
        {
            "id": "F1-assumptions",
            "description": "Illustrative what-if: one Leonkatu directed edge closed20:55–21:55 on23 May. This geometry, duration and affected classes are developer-provided scenario assumptions requiring operator confirmation for use. Exact building, actual road restrictions and perimeter remain unknown. Current September network/schedule only.",
            "affects": [
                "restriction_geometry",
                "restriction_window",
                "vehicle_permissions",
                "network_temporality",
                "transit_temporality",
            ],
        }
    ]
    road = _snapshot(pack, "road", sorted({e["id"] for e in r1 + r2 + r3}), road_assumptions)
    fire = _snapshot(
        pack,
        "fire",
        [fire_edge["id"]],
        fire_assumptions,
        {
            "source_refs": ["S02", "S21"],
            "location_text": "Leonkatu, Kalasatama, Helsinki (street-level uncertainty)",
            "geometry_ref": "case:Leonkatu:street",
            "geometry_status": "uncertain",
            "notification_time": "2026-05-23T20:55:00+03:00",
            "point": None,
            "perimeter_source": None,
            "perimeter": None,
        },
    )
    for name, scenario in [("road_scenario.json", road), ("fire_scenario.json", fire)]:
        Scenario.model_validate(scenario)
        (out / name).write_text(json.dumps(scenario, ensure_ascii=False, indent=2) + "\n")
    anchors = (
        [
            dict(OPERA, name="Opera source landmark"),
            dict(opera_anchor, name="Mannerheimintie start candidate"),
        ]
        + [dict(x, name="Pohjoinen Rautatiekatu intersection candidate") for x in south_anchors]
        + [dict(x, name="Mannerheimintie/Helsinginkatu") for x in west]
        + [dict(x, name="Sturenkatu/Helsinginkatu") for x in east]
    )
    _review_map(out / "directed_road_review.html", edges, groups, anchors)
    emap = {e["id"]: e for e in edges}
    with (out / "directed_road_mapping.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "fact_id",
                "source_id",
                "source_card_sha256",
                "source_road_name",
                "source_direction",
                "source_from_landmark",
                "source_to_landmark",
                "source_event_dates_context",
                "source_announced_date_range",
                "source_time_precision",
                "directed_edge_id",
                "osm_sumo_id",
                "road_name",
                "direction",
                "evidence_kind",
                "mapping_status",
                "exact_start",
                "exact_end",
            ],
        )
        writer.writeheader()
        for g in groups:
            for eid in g["directed_edge_ids"]:
                source = g.get("source_fact", {})
                writer.writerow(
                    {
                        "fact_id": g["fact_id"],
                        "source_id": source.get("source_id", ""),
                        "source_card_sha256": g.get("source_card_sha256", ""),
                        "source_road_name": source.get("road_name", ""),
                        "source_direction": source.get("direction") or "unknown",
                        "source_from_landmark": source.get("from_landmark") or "unknown",
                        "source_to_landmark": source.get("to_landmark") or "unknown",
                        "source_event_dates_context": ";".join(source.get("event_dates_context", [])),
                        "source_announced_date_range": ";".join(source.get("announced_date_range") or []),
                        "source_time_precision": source.get("time_precision", ""),
                        "directed_edge_id": eid,
                        "osm_sumo_id": emap[eid]["external_id"],
                        "road_name": emap[eid]["name"],
                        "direction": g["direction"],
                        "evidence_kind": "assumed" if g["fact_id"] == "F1" else "announced",
                        "mapping_status": g["review_status"],
                        "exact_start": "unknown",
                        "exact_end": "unknown",
                    }
                )
    selected = {eid: g["fact_id"] for g in groups for eid in g["directed_edge_ids"]}
    geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": eid,
                "geometry": {"type": "LineString", "coordinates": emap[eid]["geometry"]},
                "properties": {
                    "case_fact": fact,
                    "name": emap[eid]["name"],
                    "direction": "geometry order",
                    "mapping_status": "candidate",
                    "evidence_kind": "assumed_geometry",
                },
            }
            for eid, fact in selected.items()
        ],
    }
    (out / "case_geometry.geojson").write_text(json.dumps(geo, ensure_ascii=False, indent=2) + "\n")
    missing = {
        "historical_network": "NOT_VALIDATED_CURRENT_ONLY",
        "historical_gtfs": "NOT_VALIDATED_CURRENT_FEED_EXCLUDES_EVENT_DATES",
        "traffic_counts": {
            "status": "BLOCKED_SOURCE",
            "attempts": [
                {
                    "url": "https://hri.fi/data/en_GB/dataset/liikennemaarat-helsingissa",
                    "outcome": "HTTP403 web fetch",
                },
                {
                    "url": "https://hri.fi/data/api/3/action/package_show?id=liikennemaarat-helsingissa",
                    "outcome": "alternate CKAN API inaccessible via web tool",
                },
            ],
            "stop_reason": "two bounded access attempts; no event/station/time/unit coverage established",
        },
        "historical_hfp": {
            "status": "NOT_PUBLICLY_AVAILABLE_FROM_CHECKED_SOURCE",
            "url": "https://github.com/HSLdevcom/hfp-analytics",
            "reason": "official README explicitly says API currently not public",
        },
        "historical_fire_perimeter": "UNKNOWN",
        "exact_fire_building": "UNKNOWN",
        "independent_measured_traffic_validation": "NOT_VALIDATED",
    }
    (out / "missing_data_report.json").write_text(json.dumps(missing, indent=2) + "\n")
    split = {
        "schema_version": "1.0",
        "dataset_hash": sha256_file(pack_path),
        "source_hashes": {s["id"]: s["sha256"] for s in pack["sources"]},
        "extracted_source_fact_card_sha256": source_card_sha256,
        "development_cases": [
            "synthetic-toy",
            "HEL-CITYRUN-20260515-16-current-network-whatif",
            "HEL-KALASATAMA-FIRE-20260523-current-network-whatif",
        ],
        "heldout_measured_targets": [],
        "test_split_status": "NO_INDEPENDENT_MEASURED_TEST_SET",
        "freeze_status": "source bytes and example assumptions frozen; no scientific heldout claims",
        "inference_allowlist": [
            "road topology and permissions",
            "facility candidate access",
            "GTFS current schedule",
            "incident and announcement facts",
            "user-confirmed scenario assumptions",
        ],
        "inference_denylist": ["heldout outcomes", "evaluation labels"],
        "claim_ceiling": "source-informed engineering what-if, measured_prediction_validated=false",
    }
    (out / "evaluation_split_manifest.json").write_text(json.dumps(split, indent=2) + "\n")
    result = {
        "status": "PASS_EVIDENCE_SEPARATION_WITH_REVIEW_GAPS",
        "command": "python scripts/data_pipeline.py review",
        "exit_code": 0,
        "citypack_id": pack["citypack_id"],
        "road_case": {
            "source_id": source_case["source_ids"][0],
            "source_status": "rechecked_official_page2026-09-23",
            "source_card": {
                "path": str(source_card_path.relative_to(root)),
                "sha256": source_card_sha256,
                "case_id": source_case["case_id"],
                "event_dates_context": source_case["event_dates"],
                "timezone": source_case["timezone"],
            },
            "mapping": groups[:3],
            "anchors": anchors,
            "unknown_hours_preserved": True,
            "source_fact_count": len(source_case["facts"]),
            "motor_road_fact_count": sum("road_name" in fact for fact in source_case["facts"]),
            "candidate_mapped_fact_count": len(groups[:3]),
            "human_accepted_mapping_count": 0,
            "geometry_precision": None,
            "pedestrian_cycle_notice": {
                "source_id": source_case["source_ids"][0],
                "fact_id": baana["fact_id"],
                "feature": baana["feature_name"],
                "mode_scope": baana["mode_scope"],
                "times_local": baana["times_local"],
                "time_precision": "explicit_local_intervals",
                "motor_road_hours_inferred": False,
                "status": "source fact retained in original case card; not compiled into motor-drivable reference",
            },
            "direction_rule_checked_rows": len(r1),
            "source_replay_verified": False,
            "run_mode": "assumed_simultaneous_snapshot_on_current_network",
        },
        "fire_case": {
            "source_ids": ["S02", "S21"],
            "incident_facts": {
                "date": "2026-05-23",
                "notification_time_local": "20:55",
                "street": "Leonkatu",
                "building_coordinate": None,
                "actual_cordon": None,
            },
            "scenario_assumptions": fire_assumptions,
            "mapping": groups[3],
            "run_mode": "real_street_illustrative_whatif",
            "measured_prediction_validated": False,
        },
        "visualization_routing": "scientific-figure-making inspected; declared dominant GIS and web-first exclusions apply; local SVG map uses EPSG:3067",
        "missing": missing,
        "human_review_status": "PENDING",
        "artifacts": [
            {"path": str((out / n).relative_to(root)), "sha256": sha256_file(out / n)}
            for n in [
                "road_scenario.json",
                "fire_scenario.json",
                "directed_road_mapping.csv",
                "directed_road_review.html",
                "case_geometry.geojson",
                "evaluation_split_manifest.json",
                "missing_data_report.json",
            ]
        ],
    }
    (out / "case_review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result
