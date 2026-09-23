"""Small, transparent numerical/network oracles; NOT production city software.

Routing here is node-based and omits turn constraints intentionally: production
must additionally implement and test turn-aware edge-state routing. No real fire
or historical traffic predictions are made by this module.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime
import hashlib
import heapq
import json
import math
from typing import Any, Iterable, Mapping, Sequence
import numpy as np


def number(value: Any, label: str) -> float:
    if isinstance(value, (bool, str)):
        raise ValueError(f'{label}: expected finite numeric value')
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f'{label}: expected finite numeric value') from exc
    if not math.isfinite(result):
        raise ValueError(f'{label}: non-finite value')
    return result


def seed_vector(nodes: Sequence[str], seeds: Mapping[str, float]) -> np.ndarray:
    if not nodes or len(set(nodes)) != len(nodes):
        raise ValueError('nodes must be nonempty and unique')
    if set(seeds) - set(nodes):
        raise ValueError('unknown seed entity')
    a = np.array([number(seeds.get(n, 0), 'seed') for n in nodes], dtype=float)
    if np.any(a < 0) or a.sum() <= 0:
        raise ValueError('seed requires nonnegative values with positive mass')
    return a / a.sum()


def transition(nodes: Sequence[str], edges: Iterable[Mapping[str, Any]],
               type_weights: Mapping[str, float], seed: Mapping[str, float]) -> tuple[np.ndarray, np.ndarray]:
    """Normalize within each relation, then mix relation types.

    Zero-weight relation types are excluded explicitly. Empty/dangling rows restart
    to the SAME seed. All numerical input validated, no epsilon injected here.
    """
    s = seed_vector(nodes, seed)
    ix = {n: i for i, n in enumerate(nodes)}
    grouped: dict[int, dict[str, list[tuple[int, float]]]] = defaultdict(lambda: defaultdict(list))
    weights = {t: number(w, 'type_weight') for t, w in type_weights.items()}
    if any(w < 0 for w in weights.values()):
        raise ValueError('negative type weight')
    for e in edges:
        if e['src'] not in ix or e['dst'] not in ix:
            raise ValueError('orphan edge')
        typ = str(e['relation_type'])
        if typ not in weights:
            raise ValueError('unknown relation policy')
        a = number(e['strength'], 'edge_strength')
        if a < 0:
            raise ValueError('negative edge strength')
        if a > 0 and weights[typ] > 0:
            grouped[ix[e['src']]][typ].append((ix[e['dst']], a))
    p = np.zeros((len(nodes), len(nodes)), dtype=float)
    for i in range(len(nodes)):
        groups = grouped.get(i, {})
        z = sum(weights[t] for t in groups)
        if z == 0:
            p[i] = s
            continue
        for typ, outgoing in groups.items():
            within = sum(a for _, a in outgoing)
            for j, a in outgoing:
                p[i, j] += (weights[typ] / z) * (a / within)
    return p, s


def _validate(p: np.ndarray, s: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray, float]:
    p = np.asarray(p, dtype=float)
    s = np.asarray(s, dtype=float)
    alpha = number(alpha, 'alpha')
    if not 0 <= alpha < 1:
        raise ValueError('alpha must satisfy 0 <= alpha < 1')
    if p.ndim != 2 or p.shape[0] != p.shape[1] or p.shape[0] == 0:
        raise ValueError('P must be nonempty square matrix')
    if s.shape != (p.shape[0],):
        raise ValueError('seed shape mismatch')
    if not np.isfinite(p).all() or not np.isfinite(s).all() or (p < 0).any() or (s < 0).any():
        raise ValueError('P and s must be finite and nonnegative')
    if not np.allclose(p.sum(axis=1), 1, atol=1e-12, rtol=0) or not np.isclose(s.sum(), 1, atol=1e-12, rtol=0):
        raise ValueError('P row mass and seed mass must equal one')
    return p, s, alpha


def ppr_linear(p: np.ndarray, s: np.ndarray, alpha: float = 0.85) -> np.ndarray:
    """Independent dense linear-system oracle for tiny graphs only."""
    p, s, alpha = _validate(p, s, alpha)
    return np.linalg.solve(np.eye(len(s)) - alpha * p.T, (1 - alpha) * s)


def ppr_power(p: np.ndarray, s: np.ndarray, alpha: float = 0.85,
              tol: float = 1e-12, max_iter: int = 1000) -> tuple[np.ndarray, dict[str, Any]]:
    p, s, alpha = _validate(p, s, alpha)
    if tol <= 0 or not math.isfinite(tol) or max_iter < 1:
        raise ValueError('invalid iteration controls')
    r = s.copy()
    for iteration in range(1, max_iter + 1):
        r = (1 - alpha) * s + alpha * p.T @ r
        residual = float(np.linalg.norm(r - ((1 - alpha) * s + alpha * p.T @ r), ord=1))
        if residual <= tol:
            return r, {'iterations': iteration, 'residual_l1': residual, 'mass_error': abs(float(r.sum()) - 1)}
    raise RuntimeError(f'PPR did not converge: residual_l1={residual:.6g}')


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def comparable_delta(before: np.ndarray, after: np.ndarray,
                     baseline_meta: Mapping[str, Any], event_meta: Mapping[str, Any]) -> np.ndarray:
    keys = ['node_universe_hash', 'seed_hash', 'policy_hash', 'alpha', 'normalization', 'citypack_hash']
    for key in keys:
        if key not in baseline_meta or key not in event_meta or baseline_meta[key] != event_meta[key]:
            raise ValueError(f'incomparable pair: {key}')
    a, b = np.asarray(before), np.asarray(after)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('invalid rank arrays')
    for rank in (a, b):
        if rank.ndim != 1 or np.any(rank < 0) or not np.isclose(rank.sum(), 1, atol=1e-10, rtol=0):
            raise ValueError('rank vector not a distribution')
    return b - a


def parse_aware(value: str) -> datetime:
    d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError('timezone offset required')
    return d


def active(start: str, end: str, at: str) -> bool:
    a, b, t = parse_aware(start), parse_aware(end), parse_aware(at)
    if a >= b:
        raise ValueError('restriction end must be after start')
    return a <= t < b


def blocked_edges(restrictions: Sequence[Mapping[str, Any]], at: str, vehicle_class: str,
                  known_edges: set[str]) -> set[str]:
    allowed_classes = {'passenger', 'bus', 'emergency', 'bicycle', 'pedestrian'}
    if vehicle_class not in allowed_classes:
        raise ValueError('unknown vehicle class')
    result: set[str] = set()
    for r in restrictions:
        ids = set(r['edge_ids'])
        if not ids or ids - known_edges:
            raise ValueError('unknown or empty edge selection')
        classes = set(r['blocked_classes'])
        if not classes or classes - (allowed_classes | {'all'}):
            raise ValueError('unknown/empty blocked class')
        if active(r['valid_from'], r['valid_to'], at) and (vehicle_class in classes or 'all' in classes):
            result.update(ids)
    return result


def route_cost(nodes: Sequence[str], edges: Sequence[Mapping[str, Any]], start: str, end: str,
               blocked: Iterable[str] = ()) -> float | None:
    """Independent tiny-graph Dijkstra. None means UNREACHABLE, never zero."""
    if not nodes or len(nodes) != len(set(nodes)) or start not in nodes or end not in nodes:
        raise ValueError('invalid nodes/endpoints')
    edge_ids = [e['id'] for e in edges]
    if len(edge_ids) != len(set(edge_ids)):
        raise ValueError('duplicate edge IDs')
    no = set(blocked)
    if no - set(edge_ids):
        raise ValueError('unknown blocked edge')
    adjacency: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for e in edges:
        if e['src'] not in nodes or e['dst'] not in nodes:
            raise ValueError('orphan road edge')
        c = number(e['cost_s'], 'road cost')
        if c < 0:
            raise ValueError('negative road cost')
        if e['id'] not in no:
            adjacency[e['src']].append((e['dst'], c))
    distances = {start: 0.0}
    queue = [(0.0, start)]
    while queue:
        d, u = heapq.heappop(queue)
        if d != distances[u]:
            continue
        if u == end:
            return d
        for v, cost in adjacency[u]:
            nd = d + cost
            if nd < distances.get(v, math.inf):
                distances[v] = nd
                heapq.heappush(queue, (nd, v))
    return None
