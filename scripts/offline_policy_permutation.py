"""Exact offline label-permutation control for the frozen SimpleJev relation policy.

This is an engineering sensitivity check, not evidence that the model improves
decisions. It uses only the committed synthetic city and frozen API response;
there are no network calls, local model weights, or paid inference.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from collections import Counter
from pathlib import Path

from urbanimpact.fixtures import toy_city, toy_scenario
from urbanimpact.graph import paired_projection
from urbanimpact.network import Router
from urbanimpact.ranking import RELATION_DEFINITIONS, compare
from urbanimpact.util import atomic_json, digest, file_hash

ROOT = Path(__file__).resolve().parents[1]
FROZEN_POLICY = ROOT / "evidence/wp3/systemone_simplejev_relations_policy.json"
DEFAULT_REPORT = ROOT / "evidence/wp6/policy_permutation_control.json"
MODEL_ID = "featherless-ai/Qwen3.8-27B-classifier"


def frozen_scores(path: Path = FROZEN_POLICY) -> dict[str, float]:
    envelope = json.loads(path.read_text())
    policy = envelope["policy"]
    provenance = envelope["provenance"]
    if (
        policy["provider_mode"] != "simplejev_demo"
        or policy["resolved_model"] != MODEL_ID
        or provenance["resolved_model"] != MODEL_ID
        or provenance["provider_mode"] != "simplejev_demo"
        or provenance["paid_call_this_run"]
        or provenance["local_model_deployed"]
    ):
        raise ValueError("Expected the frozen free hosted SimpleJev policy")
    scores = policy["scores"]
    if set(scores) != set(RELATION_DEFINITIONS):
        raise ValueError("Frozen policy does not cover the relation ontology")
    if any(
        type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1
        for value in scores.values()
    ):
        raise ValueError("Frozen relation scores must be finite normalized weights")
    return {key: float(scores[key]) for key in sorted(scores)}


def _values(attention: dict, field: str) -> dict[str, float]:
    return {row["object_id"]: row[field] for row in attention["records"]}


def _l1(a: dict[str, float], b: dict[str, float]) -> float:
    if a.keys() != b.keys():
        raise ValueError("Policy comparisons require the same node universe")
    return sum(abs(a[node] - b[node]) for node in sorted(a))


def _top_ids(attention: dict, field: str, limit: int = 3) -> list[str]:
    values = _values(attention, field)
    return sorted(values, key=lambda node: (-values[node], node))[:limit]


def _summary(values: list[float]) -> dict:
    ordered = sorted(values)
    size = len(ordered)
    return {
        "minimum": ordered[0],
        "median": (ordered[(size - 1) // 2] + ordered[size // 2]) / 2,
        "maximum": ordered[-1],
    }


def run_control(policy_path: Path = FROZEN_POLICY) -> dict:
    scores = frozen_scores(policy_path)
    relations = sorted(scores)
    score_values = tuple(scores[relation] for relation in relations)
    city, scenario = toy_city(), toy_scenario()
    facts = Router().compare(city, scenario)
    frozen_inputs = {"city": digest(city), "scenario": digest(scenario), "physical_facts": digest(facts)}
    neutral = {relation: 1.0 for relation in relations}
    seeds = scenario.seed_spec.entity_ids

    def evaluate(weights: dict[str, float]) -> tuple[dict, dict]:
        # Rebuild the typed projection for each policy, binding baseline and
        # event to the SAME policy hash before the production compare() call.
        pair = paired_projection(city, scenario, facts, digest(weights))
        return pair, compare(pair, seeds, weights)

    neutral_pair, neutral_attention = evaluate(neutral)
    reference_graph_hashes = {side: neutral_pair[side]["graph_hash"] for side in ("baseline", "event")}
    reference_universe = neutral_attention["node_universe_hash"]
    real_attention = None
    real_pair = None
    records = []
    transition_hashes = {"baseline": set(), "event": set()}
    for order in itertools.permutations(range(len(relations))):
        weights = {relation: score_values[index] for relation, index in zip(relations, order)}
        pair, attention = evaluate(weights)
        if {
            side: pair[side]["graph_hash"] for side in ("baseline", "event")
        } != reference_graph_hashes or attention["node_universe_hash"] != reference_universe:
            raise ValueError("Permutation changed topology or node universe")
        if not attention["comparable"] or not attention["convergence"]:
            raise ValueError("Within-policy baseline/event PPR did not converge comparably")
        if digest(facts) != frozen_inputs["physical_facts"]:
            raise ValueError("Permutation changed physical facts")
        for side, hashes in transition_hashes.items():
            hashes.add(attention["transition_hashes"][side])
        metric = {
            "assignment": list(order),
            "baseline_l1_from_neutral": _l1(
                _values(attention, "baseline_attention"),
                _values(neutral_attention, "baseline_attention"),
            ),
            "event_l1_from_neutral": _l1(
                _values(attention, "attention_score"),
                _values(neutral_attention, "attention_score"),
            ),
            "delta_l1_from_neutral": _l1(
                _values(attention, "delta_attention"),
                _values(neutral_attention, "delta_attention"),
            ),
            "event_top3_changed_from_neutral": _top_ids(attention, "attention_score")
            != _top_ids(neutral_attention, "attention_score"),
        }
        records.append(metric)
        if order == tuple(range(len(relations))):
            real_attention, real_pair = attention, pair

    assert real_attention is not None and real_pair is not None
    if {"city": digest(city), "scenario": digest(scenario), "physical_facts": digest(facts)} != frozen_inputs:
        raise ValueError("Control mutated a frozen input")
    observed = records[0]
    if observed["assignment"] != list(range(len(relations))):
        raise ValueError("Identity permutation was not first")
    baseline_values = [row["baseline_l1_from_neutral"] for row in records]
    event_values = [row["event_l1_from_neutral"] for row in records]
    delta_values = [row["delta_l1_from_neutral"] for row in records]
    active_types = {
        side: sorted({link["relation_type"] for link in real_pair[side]["links"]})
        for side in ("baseline", "event")
    }
    relation_counts = {
        side: dict(sorted(Counter(link["relation_type"] for link in real_pair[side]["links"]).items()))
        for side in ("baseline", "event")
    }
    return {
        "status": "PASS_OFFLINE_NEGATIVE_CONTROL_ONLY",
        "scope": "Synthetic toy road closure; exact relation-label permutation, no new model inference",
        "source": {
            "frozen_policy_path": str(policy_path.resolve().relative_to(ROOT)),
            "frozen_policy_file_sha256": file_hash(policy_path),
            "frozen_scores_hash": digest(scores),
            "model_id": MODEL_ID,
            "provider_mode": "simplejev_demo_frozen_replay",
            "paid_calls": 0,
            "remote_calls": 0,
        },
        "fixed_inputs": {
            **frozen_inputs,
            "node_universe_hash": reference_universe,
            "graph_content_hashes": reference_graph_hashes,
            "seed_hash": real_attention["seed_hash"],
            "alpha": real_attention["alpha"],
            "epsilon": real_attention["epsilon"],
        },
        "design": {
            "relation_order": relations,
            "permutation_count": len(records),
            "method": "Exhaust all 6! score-to-relation assignments without replacement; compare baseline and event inside each assignment only.",
            "physical_method": "Compute deterministic routing facts once, retain one hash-bound immutable city/scenario/facts object across all policies.",
            "neutral_control": "All six semantic scores equal 1.0; held under the same city/scenario/facts/seeds/alpha/epsilon.",
            "metric": "L1 distance of attention vector (or event-minus-baseline delta vector) from neutral PPR.",
        },
        "graph": {
            "nodes": len(real_pair["baseline"]["nodes"]),
            "links": {side: len(real_pair[side]["links"]) for side in ("baseline", "event")},
            "active_relation_types": active_types,
            "relation_link_counts": relation_counts,
            "distinct_transition_hashes": {side: len(values) for side, values in transition_hashes.items()},
            "real_transition_hashes": real_attention["transition_hashes"],
        },
        "observed_frozen_policy": {
            "baseline_l1_from_neutral": observed["baseline_l1_from_neutral"],
            "event_l1_from_neutral": observed["event_l1_from_neutral"],
            "delta_l1_from_neutral": observed["delta_l1_from_neutral"],
            "event_top3_changed_from_neutral": observed["event_top3_changed_from_neutral"],
            "within_policy_delta_sum": real_attention["delta_sum"],
            "baseline_event_comparable": real_attention["comparable"],
        },
        "permutation_distribution": {
            "baseline_l1_from_neutral": _summary(baseline_values),
            "event_l1_from_neutral": _summary(event_values),
            "delta_l1_from_neutral": _summary(delta_values),
            "event_top3_changed_count": sum(row["event_top3_changed_from_neutral"] for row in records),
            "strictly_greater_baseline_effect_than_observed": sum(
                value > observed["baseline_l1_from_neutral"] + 1e-12 for value in baseline_values
            ),
            "approximately_equal_baseline_effect_count": sum(
                abs(value - observed["baseline_l1_from_neutral"]) <= 1e-12 for value in baseline_values
            ),
            "metrics_sha256": digest(records),
        },
        "interpretation": [
            "The frozen SimpleJev scores affect a multi-relation baseline transition and PPR, but score differences are small.",
            "The event graph has only one outgoing relation per active row, so row-normalized relation weights cancel and event PPR is invariant.",
            "Permutation sensitivity does not establish semantic correctness, predictive accuracy, causal effects, or better public decisions.",
            "This offline replay does not resolve the hosted model's unreported server/weight revision, calibration, paid production gate, or measured-traffic validation.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run_control()
    atomic_json(args.out, report)
    print(f"{args.out}: {report['status']} ({report['design']['permutation_count']} permutations)")


if __name__ == "__main__":
    main()
