"""Local Qwen System-One wire contract and strict response checks.

This module contains no model/network startup logic. It validates the typed decision
request/response that UrbanImpact sends to a deployer-local System-One server (the
reference implementation is Reflex on Qwen3.5). Runtime must not depend on TypeSafe.
"""
from __future__ import annotations
from typing import Any, Mapping
import math
from urllib.parse import urlparse
from .reference import number

CRITERIA = ['Not relevant', 'Indirectly relevant', 'Directly relevant']


def build_request(relations: Mapping[str, str], objective: str) -> dict[str, Any]:
    if not relations or len(relations) > 24 or not objective:
        raise ValueError('invalid batch/objective')
    questions = {}
    for name, description in relations.items():
        if not name or not description:
            raise ValueError('missing relation semantics')
        questions[name] = {
            'type': 'score',
            'instructions': (
                f'Assess semantic relevance of relation {name}: {description}. '
                'Use the stated objective only. Do not infer delay, casualty, failure probability, '
                'road permissions, hazard perimeter or physical outcomes.'
            ),
            'criteria': list(CRITERIA),
        }
    return {
        'state': {
            'task': 'urban_dependency_retrieval',
            'objective': objective,
            'privacy': 'Abstract relation types only; no coordinates, personal data or raw graph.',
        },
        'questions': questions,
    }


def parse_scores(response: Mapping[str, Any], expected_ids: set[str],
                 criteria: list[str] | None = None) -> dict[str, float]:
    criteria = CRITERIA if criteria is None else criteria
    if not 2 <= len(criteria) <= 10:
        raise ValueError('invalid criteria count')
    answers = response.get('answers')
    if not isinstance(answers, dict) or set(answers) != expected_ids:
        raise ValueError('question set mismatch')
    keys = {str(i) for i in range(len(criteria))}
    out = {}
    for name, answer in answers.items():
        if not isinstance(answer, dict) or answer.get('type') != 'score':
            raise ValueError('wrong answer type')
        probs = answer.get('probabilities', {})
        if not isinstance(probs, dict) or set(probs) != keys:
            raise ValueError('probability keys mismatch')
        p = {k: number(v, 'probability') for k, v in probs.items()}
        if any(v < 0 or v > 1 for v in p.values()) or abs(sum(p.values()) - 1) > 1e-6:
            raise ValueError('invalid probability distribution')
        score = number(answer.get('score'), 'score')
        confidence = number(answer.get('confidence'), 'confidence')
        if not (0 <= confidence <= 1 and 0 <= score <= len(criteria) - 1):
            raise ValueError('score/confidence out of range')
        expectation = sum(int(k) * v for k, v in p.items())
        if abs(score - expectation) > 1e-5:
            raise ValueError('score differs from rubric expectation')
        legend = answer.get('legend')
        if not isinstance(legend, dict) or set(legend) != keys:
            raise ValueError('legend mismatch')
        if any(not isinstance(v, str) or not v for v in legend.values()):
            raise ValueError('invalid legend text')
        out[name] = score / (len(criteria) - 1)
    return out


def validate_local_endpoint(base_url: str, *, allow_remote: bool = False) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
        raise ValueError('invalid System-One base URL')
    local_hosts={'127.0.0.1','localhost','::1'}
    if parsed.hostname not in local_hosts and not allow_remote:
        raise PermissionError('non-loopback System-One endpoint requires explicit --allow-remote')
    return base_url.rstrip('/') + '/v1/systemone'


def validate_runtime_budget(*, max_questions: int, max_wall_ms: int) -> None:
    if not isinstance(max_questions, int) or not 1 <= max_questions <= 24:
        raise PermissionError('invalid/absent question budget')
    if not isinstance(max_wall_ms, int) or max_wall_ms <= 0:
        raise PermissionError('invalid/absent wall-time budget')


def factor(score: float, epsilon: float = 0.1) -> float:
    score, epsilon = number(score, 'score'), number(epsilon, 'epsilon')
    if not 0 <= score <= 1 or not 0 < epsilon <= 1:
        raise ValueError('score/epsilon out of range')
    return epsilon + (1 - epsilon) * score
