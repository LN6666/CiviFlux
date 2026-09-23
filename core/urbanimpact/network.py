"""Deterministic directed, turn-aware, fixed-weight routing; never a safety predictor."""

from __future__ import annotations

import heapq
from collections import defaultdict
from datetime import datetime
from typing import Iterable, get_args

from urbanimpact.contracts import CityPack, Scenario, VehicleClass
from urbanimpact.util import digest


def physical_context_hash(city: CityPack, scenario: Scenario) -> str:
    """Identify physical inputs using the same field scope as the routing cache."""
    physical = scenario.model_dump(mode="json")
    for field in ("ranking", "objective", "scenario_id"):
        physical.pop(field)
    return digest({"city": digest(city), "physical": physical})


def compile_restrictions(
    city: CityPack, scenario: Scenario, vehicle_class: str = "passenger", at: datetime | None = None
) -> frozenset[str]:
    """Compile closures at [start, end); validate even inactive references."""
    if vehicle_class not in get_args(VehicleClass):
        raise ValueError(f"Unknown vehicle class: {vehicle_class}")
    if city.citypack_id != scenario.citypack_id:
        raise ValueError("Scenario belongs to a different citypack")
    edges = {e.id for e in city.edges}
    for restriction in scenario.restrictions:
        if not set(restriction.edge_ids) <= edges:
            raise ValueError(f"Unknown restriction edges: {sorted(set(restriction.edge_ids) - edges)}")
    instant = at or scenario.analysis_at
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Timezone-aware analysis time required")
    return frozenset(
        edge
        for r in scenario.restrictions
        if r.valid_from <= instant < r.valid_to and vehicle_class in r.blocked_classes
        for edge in r.edge_ids
    )


def _missing(status: str, reason: str) -> dict:
    return dict(
        status=status,
        reachable=False if status == "unreachable" else None,
        edge_ids=[],
        distance_m=None,
        travel_time_s=None,
        reason=reason,
    )


class Router:
    """Dijkstra over incoming-edge states, preserving explicit turn/class constraints."""

    def __init__(self, city: CityPack | None = None):
        self.city = city

    @staticmethod
    def _index(city: CityPack, vehicle_class: str) -> tuple:
        if vehicle_class not in get_args(VehicleClass):
            raise ValueError(f"Unknown vehicle class: {vehicle_class}")
        nodes = {n.id for n in city.nodes}
        edges = {e.id: e for e in city.edges}
        outgoing = defaultdict(list)
        for edge in sorted(city.edges, key=lambda e: e.id):
            if vehicle_class in edge.allowed_vehicle_classes:
                outgoing[edge.source].append(edge)
        turns = (
            None
            if city.connections is None
            else {
                (c.from_edge, c.to_edge)
                for c in city.connections
                if vehicle_class in c.allowed_vehicle_classes
            }
        )
        return nodes, edges, outgoing, turns

    @staticmethod
    def _search(index: tuple, origin: str, targets: Iterable[str | None], blocked: Iterable[str]) -> dict:
        nodes, edges, outgoing, turns = index
        if origin not in nodes:
            raise ValueError(f"Unknown origin: {origin}")
        forbidden = set(blocked)
        if not forbidden <= edges.keys():
            raise ValueError("Unknown blocked edge")
        waiting = set(targets)
        results = {}
        if None in waiting:
            results[None] = _missing("unavailable", "Facility entrance is unknown")
            waiting.remove(None)
        if not waiting <= nodes:
            raise ValueError("Unknown target")
        # Edge-state labels preserve turn constraints; one search covers every facility.
        queue = [(0.0, (), origin, "")]
        best = {"": (0.0, ())}
        while queue and waiting:
            cost, path, node, incoming = heapq.heappop(queue)
            if best.get(incoming) != (cost, path):
                continue
            if node in waiting:
                results[node] = dict(
                    status="available",
                    reachable=True,
                    edge_ids=list(path),
                    distance_m=sum(edges[e].length_m for e in path),
                    travel_time_s=cost,
                )
                waiting.remove(node)
            for edge in outgoing[node]:
                if edge.id in forbidden or (
                    incoming and turns is not None and (incoming, edge.id) not in turns
                ):
                    continue
                candidate = (cost + edge.travel_time_s, path + (edge.id,))
                if candidate < best.get(edge.id, (float("inf"), ())):
                    best[edge.id] = candidate
                    heapq.heappush(queue, (*candidate, edge.target, edge.id))
        for target in waiting:
            results[target] = _missing("unreachable", "No permitted directed route at the declared time")
        return results

    def route(
        self,
        city: CityPack,
        origin: str,
        target: str | None,
        vehicle_class: str = "passenger",
        blocked: Iterable[str] = (),
    ) -> dict:
        return self._search(self._index(city, vehicle_class), origin, [target], blocked)[target]

    def compare(
        self,
        city: CityPack,
        scenario: Scenario,
        vehicle_class: str = "passenger",
        origins: Iterable[str] | None = None,
    ) -> dict:
        blocked = compile_restrictions(city, scenario, vehicle_class)
        nodes = {n.id for n in city.nodes}
        edges = {e.id: e for e in city.edges}
        facilities = {f.id: f for f in city.facilities}
        if origins is None:
            selected = []
            for seed in scenario.seed_spec.entity_ids:
                if seed in nodes:
                    selected.append(seed)
                elif seed in edges:
                    selected.append(edges[seed].source)
                elif seed in facilities and facilities[seed].entrance_node_id:
                    selected.append(facilities[seed].entrance_node_id)
            origins = selected or [min(nodes)]
            origin_policy = "resolved scenario seeds; lexicographic node fallback if no seed resolves"
        else:
            origin_policy = "explicit origins"
        origins = sorted(set(origins))
        if not origins or not set(origins) <= nodes:
            raise ValueError("At least one known origin required")
        od = []
        index = self._index(city, vehicle_class)
        targets = {f.entrance_node_id for f in city.facilities}
        for origin in origins:
            baseline_routes = self._search(index, origin, targets, ())
            event_routes = self._search(index, origin, targets, blocked)
            for facility in sorted(city.facilities, key=lambda f: f.id):
                baseline = baseline_routes[facility.entrance_node_id]
                event = event_routes[facility.entrance_node_id]
                available = baseline["status"] == event["status"] == "available"
                od.append(
                    dict(
                        origin=origin,
                        target=facility.entrance_node_id,
                        facility_id=facility.id,
                        entrance_status=facility.access_status,
                        baseline=baseline,
                        event=event,
                        delta_travel_time_s=event["travel_time_s"] - baseline["travel_time_s"]
                        if available
                        else None,
                        delta_distance_m=event["distance_m"] - baseline["distance_m"] if available else None,
                    )
                )
        transit = []
        bus_blocked = compile_restrictions(city, scenario, "bus")
        for route in city.transit.get("routes", []):
            overlap = sorted(blocked.intersection(route.get("edge_ids", [])))
            if overlap:
                transit.append(
                    dict(
                        route_id=route.get("id", route.get("route_id")),
                        edge_ids=overlap,
                        match_status=route.get("match_status", "candidate"),
                        bus_permission_affected=bool(bus_blocked.intersection(overlap)),
                        interpretation="road association; selected vehicle restrictions do not imply bus delay or cancellation",
                    )
                )
        for relation in city.transit.get("road_matches", []):
            overlap = sorted(blocked.intersection(relation.get("edge_ids", [])))
            if overlap:
                transit.append(
                    dict(
                        route_id=relation["route_id"],
                        edge_ids=overlap,
                        match_status=relation.get("match_status", "candidate"),
                        bus_permission_affected=bool(bus_blocked.intersection(overlap)),
                        interpretation="potential association; not measured delay or cancellation",
                    )
                )
        for relation in city.transit.get("shape_matches", []):
            overlap = sorted(blocked.intersection(relation.get("candidate_edge_ids", [])))
            for route_id in sorted(relation.get("route_ids", [])) if overlap else []:
                transit.append(
                    dict(
                        route_id=route_id,
                        shape_id=relation.get("shape_id"),
                        edge_ids=overlap,
                        match_status="candidate",
                        candidates_truncated=relation.get("truncated", False),
                        bus_permission_affected=bool(bus_blocked.intersection(overlap)),
                        interpretation="geometry proximity candidate; route use, delay and cancellation unverified",
                    )
                )
        return dict(
            od=od,
            vehicle_class=vehicle_class,
            analysis_at=scenario.analysis_at.isoformat(),
            restrictions=sorted(blocked),
            all_facilities_checked=len(city.facilities),
            origins=origins,
            origin_policy=origin_policy,
            transit=transit,
            transit_coverage="candidate matching only; absent or truncated matches remain unknown",
            facilities=[
                dict(facility_id=f.id, entrance_status=f.access_status, entrance_node_id=f.entrance_node_id)
                for f in city.facilities
            ],
            network_hash=digest(city),
            physical_context_hash=physical_context_hash(city, scenario),
            units={"distance": "m", "travel_time": "s"},
            model="directed_turn_aware_fixed_travel_time",
            limitations=[
                "Fixed weights are not real-time congestion or emergency response time.",
                "Emergency vehicles have only explicitly imported access permissions.",
                "Unknown facility entrances produce unavailable metrics, never zero.",
                "Unmapped transit routes have unknown impacts.",
            ],
            turn_policy="explicit connection allowlist"
            if city.connections is not None
            else "topological connections; turn restrictions unavailable",
        )


def compare_boundaries(
    inner: CityPack,
    outer: CityPack,
    scenario: Scenario,
    origins: Iterable[str],
    threshold_seconds: float = 1.0,
    vehicle_class: str = "passenger",
) -> dict:
    """Compare identical ODs and restrictions on nested crops, declaring missing facilities unstable."""
    if threshold_seconds < 0:
        raise ValueError("Threshold must be nonnegative")
    origins = tuple(origins)
    inner_scenario = scenario.model_copy(update={"citypack_id": inner.citypack_id})
    outer_scenario = scenario.model_copy(update={"citypack_id": outer.citypack_id})
    results = [
        Router().compare(c, s, vehicle_class, origins)
        for c, s in ((inner, inner_scenario), (outer, outer_scenario))
    ]
    indexes = [{(r["origin"], r["facility_id"]): r for r in result["od"]} for result in results]
    differences = []
    for key in sorted(indexes[0].keys() | indexes[1].keys()):
        a, b = (index.get(key) for index in indexes)
        if a is None or b is None:
            differences.append(dict(origin=key[0], facility_id=key[1], reason="facility missing from crop"))
            continue
        for stage in ("baseline", "event"):
            ra, rb = a[stage], b[stage]
            if ra["status"] != rb["status"] or (
                ra["status"] == "available"
                and abs(ra["travel_time_s"] - rb["travel_time_s"]) > threshold_seconds
            ):
                differences.append(dict(origin=key[0], facility_id=key[1], stage=stage, inner=ra, outer=rb))
    return dict(
        status="stable" if not differences else "not_stable",
        threshold_seconds=threshold_seconds,
        compared_od_count=len(indexes[1]),
        differences=differences,
        inner_network_hash=digest(inner),
        outer_network_hash=digest(outer),
        scope="fixed-weight OD access; not a whole-city convergence guarantee",
    )
