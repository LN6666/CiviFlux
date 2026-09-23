"""Independent tiny-network oracle: exhaustive edge-simple paths, no product imports."""

from __future__ import annotations

import math
from datetime import datetime


def active_blocked(scenario: dict) -> set[str]:
    when = datetime.fromisoformat(scenario["analysis_at"].replace("Z", "+00:00"))
    vehicle = scenario.get("analysis_vehicle_class", "passenger")
    return {
        eid
        for r in scenario["restrictions"]
        if datetime.fromisoformat(r["valid_from"].replace("Z", "+00:00"))
        <= when
        < datetime.fromisoformat(r["valid_to"].replace("Z", "+00:00"))
        and vehicle in r["blocked_classes"]
        for eid in r["edge_ids"]
    }


def route(city: dict, origin: str, target: str | None, vehicle: str, blocked: set[str]) -> dict:
    if target is None:
        return {"status": "unavailable", "travel_time_s": None, "distance_m": None, "edge_ids": []}
    allowed = [e for e in city["edges"] if vehicle in e["allowed_vehicle_classes"] and e["id"] not in blocked]
    turns = (
        None
        if city["connections"] is None
        else {
            (c["from_edge"], c["to_edge"])
            for c in city["connections"]
            if vehicle in c["allowed_vehicle_classes"]
        }
    )
    outcomes = []

    def visit(node, path, cost, distance):
        if node == target:
            outcomes.append((cost, tuple(path), distance))
            return
        for edge in allowed:
            if edge["source"] != node or edge["id"] in path:
                continue
            if path and turns is not None and (path[-1], edge["id"]) not in turns:
                continue
            visit(
                edge["target"],
                path + [edge["id"]],
                cost + edge.get("cost_s", edge["length_m"] / (edge["speed_kph"] / 3.6)),
                distance + edge["length_m"],
            )

    visit(origin, [], 0.0, 0.0)
    if not outcomes:
        return {"status": "unreachable", "travel_time_s": None, "distance_m": None, "edge_ids": []}
    cost, path, distance = min(outcomes)
    return {"status": "available", "travel_time_s": cost, "distance_m": distance, "edge_ids": list(path)}


def labels(city: dict, scenario: dict) -> dict:
    edges = {e["id"]: e for e in city["edges"]}
    origins = sorted({edges[seed]["source"] for seed in scenario["seed_spec"]["entity_ids"]})
    result = []
    affected = []
    unknown = []
    for origin in origins:
        for facility in sorted(city["facilities"], key=lambda f: f["id"]):
            before = route(
                city,
                origin,
                facility["entrance_node_id"],
                scenario.get("analysis_vehicle_class", "passenger"),
                set(),
            )
            after = route(
                city,
                origin,
                facility["entrance_node_id"],
                scenario.get("analysis_vehicle_class", "passenger"),
                active_blocked(scenario),
            )
            unavailable = "unavailable" in {before["status"], after["status"]}
            changed = (
                False
                if unavailable
                else before["status"] != after["status"]
                or (
                    before["status"] == "available"
                    and not math.isclose(
                        before["travel_time_s"], after["travel_time_s"], rel_tol=0, abs_tol=1e-10
                    )
                )
            )
            if unavailable:
                unknown.append(facility["id"])
            if changed:
                affected.append(facility["id"])
            result.append(
                {
                    "origin": origin,
                    "facility_id": facility["id"],
                    "baseline": before,
                    "event": after,
                    "affected": changed,
                    "label_available": not unavailable,
                }
            )
    return {
        "origin_policy": "source node of fixed seed edge",
        "label_method": "independent exhaustive edge-simple path enumeration",
        "label_authority": "machine oracle; not human labelled and not measured data",
        "affected_facility_ids": sorted(set(affected)),
        "unknown_facility_ids": sorted(set(unknown)),
        "od": result,
    }
