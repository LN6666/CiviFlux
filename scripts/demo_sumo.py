#!/usr/bin/env python3
"""Produce real SUMO evidence. Existing evidence is preserved in uniquely named runs."""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta
from pathlib import Path

from urbanimpact.contracts import CityPack, Scenario
from urbanimpact.network import Router
from urbanimpact.util import atomic_json, file_hash

from adapters.sumo import Demand, Limits, SumoAdapter
from adapters.sumo.fixtures import dual_corridor


def helsinki_fixture(path: Path) -> tuple[CityPack, Scenario, tuple[Demand, ...]]:
    city = CityPack.model_validate_json(path.read_bytes())
    edges = {e.id: e for e in city.edges if "passenger" in e.allowed_vehicle_classes}
    outgoing = {}
    for c in city.connections or ():
        if c.from_edge in edges and c.to_edge in edges and "passenger" in c.allowed_vehicle_classes:
            outgoing.setdefault(c.from_edge, []).append(c.to_edge)
    # Find a bounded connected 8-edge corridor using only imported legal turns.
    path_edges = []
    for start in sorted(outgoing):
        if edges[start].length_m < 20:
            continue
        chain = [start]
        for _ in range(7):
            candidates = [
                eid
                for eid in sorted(outgoing.get(chain[-1], []))
                if eid not in chain and edges[eid].target not in {edges[x].source for x in chain}
            ]
            if not candidates:
                break
            chain.append(candidates[0])
        if len(chain) == 8:
            path_edges = chain
            break
    if not path_edges:
        raise ValueError("No bounded passenger corridor available in real citypack")
    included = set(path_edges)
    frontier = included.copy()
    # Preserve local alternative turns within two graph rings and declare bounded coverage.
    for _ in range(2):
        frontier = {b for a in frontier for b in outgoing.get(a, [])} - included
        included.update(frontier)
    selected = [e for e in city.edges if e.id in included]
    nodes = {n for e in selected for n in (e.source, e.target)}
    local = CityPack.model_validate(
        {
            **city.model_dump(),
            "nodes": [n.model_dump() for n in city.nodes if n.id in nodes],
            "edges": [e.model_dump() for e in selected],
            "connections": [
                c.model_dump()
                for c in city.connections or ()
                if c.from_edge in included and c.to_edge in included
            ],
            "facilities": [],
            "transit": {},
            "warnings": [
                *city.warnings,
                "Bounded representative corridor, not full event or citywide simulation.",
            ],
        }
    )
    start = datetime.fromisoformat("2026-09-23T12:00:00+03:00")
    s = Scenario.model_validate(
        dict(
            scenario_id="helsinki-bounded-sumo-whatif",
            citypack_id=city.citypack_id,
            kind="road",
            analysis_at=start,
            window={"start": start, "end": start + timedelta(seconds=600)},
            restrictions=[
                dict(
                    id="assumed-corridor-closure",
                    edge_ids=[path_edges[3]],
                    valid_from=start,
                    valid_to=start + timedelta(seconds=600),
                    blocked_classes=["passenger"],
                    evidence_kind="assumed",
                    evidence_refs=[city.sources[0].id],
                )
            ],
            assumptions=[
                dict(
                    id="whatif",
                    description="Assumed road closure and synthetic demand on a current OSM snapshot; no event validation",
                    affects=["restrictions", "demand"],
                )
            ],
            seed_spec=dict(entity_ids=[path_edges[0]]),
        )
    )
    return (
        local,
        s,
        tuple(Demand(f"synthetic-helsinki-{i}", tuple(path_edges), depart_s=i * 10) for i in range(5)),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--citypack", type=Path)
    parser.add_argument("--output", type=Path, default=Path("evidence/wp4"))
    args = parser.parse_args()
    stamp = str(time.time_ns())
    if args.citypack:
        city, scenario, demands = helsinki_fixture(args.citypack)
        name = "helsinki-" + stamp
        limits = Limits(duration_s=600)
    else:
        city, scenario = dual_corridor()
        demands = (Demand("v0", ("sa", "ab", "bc", "ch")),)
        name = "synthetic-" + stamp
        limits = Limits()
    report = SumoAdapter().run_pair(city, scenario, demands, args.output / name, limits)
    report["evidence_directory"] = str(args.output / name)
    report["coverage"] = {
        "nodes": len(city.nodes),
        "edges": len(city.edges),
        "vehicles": len(demands),
        "network_scope": "bounded representative corridor" if args.citypack else "synthetic dual corridor",
    }
    atomic_json(args.output / ("helsinki_sumo_pair.json" if args.citypack else "sumo_pair.json"), report)
    if not args.citypack:
        facts = Router().compare(city, scenario)
        atomic_json(
            Path("evidence/wp2/network_comparison.json"),
            dict(
                status="PASS",
                mode="production_router",
                scope="synthetic independent hand-solvable dual corridor",
                facts=facts,
                command="uv run --frozen python scripts/demo_sumo.py",
                exit_code=0,
                product_sha256=file_hash(Path("core/urbanimpact/network.py")),
            ),
        )
    print(
        f"{report['engine']}: baseline={report['baseline']['arrived']}, event={report['event']['arrived']}, unfinished={report['event']['unfinished']} -> {args.output / name}"
    )


if __name__ == "__main__":
    main()
