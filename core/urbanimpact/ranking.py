"""Sparse relation-mixture PPR; physical facts are not inputs to model policy edits."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy import sparse

from .util import digest

RELATION_DEFINITIONS = {
    "ROAD_CONNECTS_TO": "A directed road segment legally connects to another segment.",
    "ROUTE_USES_SEGMENT": "A verified transit route uses a road segment.",
    "SEGMENT_USED_BY_ROUTE": "A road segment is used by a verified transit route.",
    "STOP_ON_ROUTE": "A transit stop belongs to a transit route.",
    "FACILITY_ACCESSED_VIA": "A facility is accessed via a segment on a verified network path.",
    "SEGMENT_ACCESS_TO_FACILITY": "A segment lies on a verified network path to a facility.",
}


def transition(graph: dict, scores: dict[str, float], epsilon=0.1):
    if not 0 < epsilon <= 1:
        raise ValueError("epsilon outside (0,1]")
    nodes = [o["object_id"] for o in graph["nodes"]]
    index = {n: i for i, n in enumerate(nodes)}
    rows = defaultdict(lambda: defaultdict(list))
    for e in graph["links"]:
        t = e["relation_type"]
        weight = float(e["base_strength"])
        if t not in scores:
            raise ValueError("Policy missing relation")
        s = float(scores[t])
        if not np.isfinite(s) or not 0 <= s <= 1 or not np.isfinite(weight) or weight < 0:
            raise ValueError("Invalid semantic weight")
        if e["src"] not in index or e["dst"] not in index:
            raise ValueError("Unknown graph endpoint")
        if weight > 0:
            rows[index[e["src"]]][t].append((index[e["dst"]], weight))
    row = []
    col = []
    data = []
    for i, relations in rows.items():
        norm = sum(epsilon + (1 - epsilon) * scores[t] for t in relations)
        for t, edges in relations.items():
            mixture = (epsilon + (1 - epsilon) * scores[t]) / norm
            total = sum(w for _, w in edges)
            for j, w in edges:
                row.append(i)
                col.append(j)
                data.append(mixture * w / total)
    matrix = sparse.csr_array((data, (row, col)), shape=(len(nodes), len(nodes)), dtype=float)
    matrix.sum_duplicates()
    matrix.sort_indices()
    return matrix


def ppr(matrix, seed, alpha=0.85, tolerance=1e-12, max_iter=1000):
    matrix = sparse.csr_array(matrix, dtype=float)
    seed = np.asarray(seed, dtype=float)
    if (
        not np.isfinite(alpha)
        or not 0 < alpha < 1
        or not np.isfinite(tolerance)
        or tolerance <= 0
        or type(max_iter) != int
        or max_iter < 1
    ):
        raise ValueError("Invalid solver configuration")
    if matrix.shape != (len(seed), len(seed)) or not len(seed):
        raise ValueError("Dimension mismatch")
    if np.any(~np.isfinite(seed)) or np.any(seed < 0) or seed.sum() <= 0:
        raise ValueError("Invalid seed")
    if np.any(~np.isfinite(matrix.data)) or np.any(matrix.data < 0):
        raise ValueError("Invalid transition")
    sums = np.asarray(matrix.sum(axis=1)).ravel()
    dangling = sums == 0
    if np.any(np.abs(sums[~dangling] - 1) > 1e-12):
        raise ValueError("Non stochastic rows")
    seed = seed / seed.sum()
    rank = seed.copy()
    for iteration in range(1, max_iter + 1):
        updated = (1 - alpha) * seed + alpha * (matrix.T @ rank + rank[dangling].sum() * seed)
        residual = float(np.abs(updated - rank).sum())
        rank = updated
        if residual <= tolerance:
            actual = float(
                np.abs(
                    (1 - alpha) * seed + alpha * (matrix.T @ rank + rank[dangling].sum() * seed) - rank
                ).sum()
            )
            return {
                "scores": rank,
                "residual_l1": actual,
                "iterations": iteration,
                "convergence": True,
                "mass_error": abs(float(rank.sum()) - 1),
            }
    raise ValueError(f"PPR did not converge; residual_l1={residual}")


def matrix_hash(matrix):
    return digest(
        {
            "shape": matrix.shape,
            "indptr": matrix.indptr.tolist(),
            "indices": matrix.indices.tolist(),
            "data": matrix.data.tolist(),
        }
    )


def compare(pair, seeds, scores, *, alpha=0.85, epsilon=0.1):
    before = pair["baseline"]
    after = pair["event"]
    from .contracts import MANIFEST, Link, OntologyObject, ProjectionSpec
    from .graph import project

    if before["spec"] != after["spec"]:
        raise ValueError("Paired comparison context differs")
    if before["spec"]["relation_policy_hash"] != digest(scores):
        raise ValueError("Policy is not bound to projection")
    if pair.get("projection_hash") != digest({k: v for k, v in pair.items() if k != "projection_hash"}):
        raise ValueError("Projection content hash mismatch")
    for graph in (before, after):
        spec = ProjectionSpec.model_validate(graph["spec"])
        if spec.ontology_version != MANIFEST["ontology_version"]:
            raise ValueError("Ontology version mismatch")
        payload = {"nodes": graph["nodes"], "links": graph["links"]}
        ids = [o["object_id"] for o in graph["nodes"]]
        if ids != sorted(set(ids)):
            raise ValueError("Node IDs must be unique and ordered")
        if graph["graph_hash"] != digest(payload):
            raise ValueError("Graph content hash mismatch")
        if graph["node_universe_hash"] != digest(ids):
            raise ValueError("Node universe hash mismatch")
        validated = project(
            [OntologyObject.model_validate(o) for o in graph["nodes"]],
            [Link.model_validate(e) for e in graph["links"]],
            spec,
        )
        if validated != graph:
            raise ValueError("Graph does not conform to its typed projection")
        if spec.projection_kind != "operational":
            raise ValueError("Operational ranking requires an operational projection")
    nodes = [o["object_id"] for o in before["nodes"]]
    if nodes != [o["object_id"] for o in after["nodes"]]:
        raise ValueError("Paired universe differs")
    if set(seeds) - set(nodes) or not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("Seeds outside projection")
    seed = np.array([1 / len(seeds) if n in seeds else 0 for n in nodes])
    policy_hash = digest(scores)
    calculated = {}
    hashes = {}
    for side in ("baseline", "event"):
        matrix = transition(pair[side], scores, epsilon)
        calculated[side] = ppr(matrix, seed, alpha)
        hashes[side] = matrix_hash(matrix)
    b = calculated["baseline"]["scores"]
    a = calculated["event"]["scores"]
    rows = []
    by_type = defaultdict(list)
    for i, o in enumerate(before["nodes"]):
        by_type[o["object_type"]].append(i)
    type_ranks = {
        i: pos + 1
        for indexes in by_type.values()
        for pos, i in enumerate(sorted(indexes, key=lambda i: (-a[i], nodes[i])))
    }
    from .graph import witness_paths

    explain_ids = set(sorted(range(len(nodes)), key=lambda i: (-a[i], nodes[i]))[:30]) | {
        i
        for i, o in enumerate(before["nodes"])
        if o["object_type"] in ("Hospital", "FireStation", "Facility")
    }
    for i, n in enumerate(nodes):
        rows.append(
            {
                "object_id": n,
                "object_type": before["nodes"][i]["object_type"],
                "baseline_attention": float(b[i]),
                "attention_score": float(a[i]),
                "delta_attention": float(a[i] - b[i]),
                "rank_within_type": type_ranks[i],
                "explanation_paths": witness_paths(after, list(seeds), n) if i in explain_ids else [],
            }
        )
    return {
        "kind": "attention_not_risk",
        "records": rows,
        "policy_hash": policy_hash,
        "seed_hash": digest(seed.tolist()),
        "node_universe_hash": before["node_universe_hash"],
        "alpha": alpha,
        "epsilon": epsilon,
        "transition_hashes": hashes,
        "residual_l1": {k: v["residual_l1"] for k, v in calculated.items()},
        "iterations": {k: v["iterations"] for k, v in calculated.items()},
        "convergence": True,
        "delta_sum": float((a - b).sum()),
        "comparable": True,
        "structural_change_identified": bool(pair["graph_delta_log"]),
    }
