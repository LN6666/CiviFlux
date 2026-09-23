"""Application use case. Dependencies enter through adapters; domain layers remain UI-free."""

from __future__ import annotations

import json
import shutil
from importlib.metadata import version
from pathlib import Path
from threading import Event
from typing import Callable, Protocol

from .contracts import MANIFEST, CityPack, ResultBundle, Scenario
from .graph import paired_projection
from .network import Router
from .ranking import RELATION_DEFINITIONS, compare
from .util import atomic_json, digest, file_hash


def physical_engine_hash() -> str:
    """Invalidate physical caches when code or numerical/simulation dependencies change."""
    from adapters.sumo import adapter

    from . import contracts, network

    modules = (contracts, network, adapter)
    return digest(
        {
            "modules": {m.__name__: file_hash(Path(m.__file__)) for m in modules},
            "dependencies": {name: version(name) for name in ("eclipse-sumo", "sumolib", "pyproj")},
        }
    )


def copy_simulation_artifacts(source: Path, target: Path, artifacts: dict) -> None:
    """Copy only hash-bound simulation files, never arbitrary paths from a cached report."""
    target.mkdir(parents=True, exist_ok=True)
    for name, expected in artifacts.items():
        if Path(name).name != name or name in (".", ".."):
            raise ValueError("Invalid simulation artifact name")
        origin = source / name
        if not origin.is_file() or origin.is_symlink() or file_hash(origin) != expected:
            raise ValueError("Simulation artifact integrity failure")
        shutil.copyfile(origin, target / name)


class SemanticPolicyBackend(Protocol):
    def score_relations(self, objective: str, relation_definitions: dict[str, str]) -> dict: ...


class AnalysisCancelled(Exception):
    pass


class AnalysisService:
    def __init__(self, cache_dir: Path, policy_backend: SemanticPolicyBackend | None = None):
        self.cache_dir = cache_dir
        self.policy_backend = policy_backend

    def run(
        self,
        city: CityPack,
        scenario: Scenario,
        run_id: str,
        folder: Path,
        *,
        overlay_hash: str,
        action_log_hash: str,
        extra_limitations: tuple[str, ...] = (),
        stage: Callable[[str], None] = lambda _: None,
        cancel: Event | None = None,
    ) -> ResultBundle:
        def checkpoint(name):
            if cancel and cancel.is_set():
                raise AnalysisCancelled("Run cancelled")
            stage(name)

        folder.mkdir(parents=True, exist_ok=True)
        physical_data = scenario.model_dump(mode="json")
        for field in ("ranking", "objective", "scenario_id"):
            physical_data.pop(field, None)
        physical_key = digest(
            {"city": digest(city), "physical": physical_data, "engine_revision": physical_engine_hash()}
        )
        cache = self.cache_dir / physical_key / "facts.json"
        checkpoint("routing")
        if cache.exists():
            saved = json.loads(cache.read_text())
            if saved["sha256"] != digest(saved["facts"]):
                raise ValueError("Physical cache integrity failure")
            facts = saved["facts"]
            cache_hit = True
            if scenario.engine == "routing_sumo":
                copy_simulation_artifacts(
                    cache.parent / "sumo", folder / "sumo", facts["simulation"]["artifacts"]
                )
        else:
            facts = Router().compare(city, scenario, vehicle_class=scenario.analysis_vehicle_class)
            cache_hit = False
            if scenario.engine == "routing_sumo":
                checkpoint("sumo")
                from adapters.sumo import SumoAdapter, synthetic_demand

                demand = synthetic_demand(city, scenario, vehicle_class=scenario.analysis_vehicle_class)
                facts["simulation"] = SumoAdapter().run_pair(
                    city, scenario, demand, folder / "sumo", cancel_event=cancel
                )
                copy_simulation_artifacts(
                    folder / "sumo", cache.parent / "sumo", facts["simulation"]["artifacts"]
                )
            atomic_json(cache, {"sha256": digest(facts), "facts": facts})
        facts["physical_cache"] = {"key": physical_key, "hit": cache_hit}
        checkpoint("projection")
        scores = {name: 1.0 for name in RELATION_DEFINITIONS}
        policy = None
        provider = "rules"
        if scenario.ranking in ("A3", "A4"):
            checkpoint("system_one_api")
            if self.policy_backend is None:
                raise RuntimeError("BLOCKED_API_SETUP: configure SimpleJev endpoint and call budget")
            policy = self.policy_backend.score_relations(scenario.objective, RELATION_DEFINITIONS)
            scores = policy["scores"]
            provider = policy["provider_mode"]
        pair = paired_projection(city, scenario, facts, digest(scores))
        checkpoint("ranking")
        if scenario.ranking in ("A2", "A3", "A5"):
            attention = compare(pair, scenario.seed_spec.entity_ids, scores)
            if policy:
                policy["applied_transition_hash"] = digest(attention["transition_hashes"])
        elif scenario.ranking == "A1":
            from collections import deque

            adj = {}
            for e in pair["event"]["links"]:
                adj.setdefault(e["src"], []).append(e["dst"])
            seen = set(scenario.seed_spec.entity_ids)
            q = deque(seen)
            while q:
                for dst in adj.get(q.popleft(), []):
                    if dst not in seen:
                        seen.add(dst)
                        q.append(dst)
            attention = {
                "kind": "typed_reachability_not_risk",
                "reachable_ids": sorted(seen),
                "records": [],
                "convergence": None,
            }
        elif scenario.ranking == "A4":
            attention = {
                "kind": "relation_policy_without_ppr",
                "relation_scores": scores,
                "records": [],
                "convergence": None,
            }
        else:
            attention = {"kind": "physical_facts_only", "records": [], "convergence": None}
        attention["variant"] = scenario.ranking
        if scenario.ranking == "A5":
            attention["control"] = "neutral semantic weights; identical to fixed PPR by construction"
        checkpoint("exporting")
        result = ResultBundle(
            run_id=run_id,
            scenario_id=scenario.scenario_id,
            citypack_id=city.citypack_id,
            ontology_version=MANIFEST["ontology_version"],
            scenario_overlay_hash=overlay_hash,
            action_log_hash=action_log_hash,
            projection_id="road_fire_operational",
            projection_hash=pair["projection_hash"],
            source_snapshot_hash=digest(city),
            demand_kind="synthetic",
            network_temporality=city.network_temporality,
            transit_temporality=city.transit_temporality,
            simulation_status="completed" if scenario.engine == "routing_sumo" else "not_requested",
            provider_mode=provider,
            facts=facts,
            attention=attention,
            graph=pair,
            assumptions=scenario.assumptions,
            sources=city.sources,
            limitations=tuple(city.warnings)
            + extra_limitations
            + (
                "Planning/research support; not operational dispatch or evacuation guidance.",
                "Fixed network travel time is not congestion or emergency response time.",
                "Attention is semantic relevance, not risk or causality.",
                "No independent measured traffic validation.",
            ),
            policy=policy,
        )
        atomic_json(folder / "result.json", result)
        atomic_json(folder / "scenario.json", scenario)
        atomic_json(folder / "ontology.json", MANIFEST)
        if policy and hasattr(self.policy_backend, "last_provenance"):
            atomic_json(folder / "model_provenance.json", self.policy_backend.last_provenance)
        return result
