"""Strict HTTP boundary for abstract relation relevance, never physical city facts.

Only score probabilities enter the returned policy. Credentials, request text, raw
city data and unconstrained server metadata never enter persisted provenance.
Runtime pins are deployment declarations, not proof of a running model. Live
release evidence must separately verify the deployed runtime and graph application.
"""

from __future__ import annotations

import copy
import ipaddress
import json
import math
import os
import re
import socket
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

CRITERIA = ("Not relevant", "Indirectly relevant", "Directly relevant")
MODEL = "Qwen/Qwen3.5-4B"
REFLEX_REVISION = "19586a1374dca138eddf5d7b8889cae8dfa505f6"
MODEL_REVISION = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
RUBRIC_VERSION = "urbanimpact-relation-relevance-v1"


class BlockedEnvironment(RuntimeError):
    """No live typed model response was available; never implies a fallback PASS."""


class ProtocolError(ValueError):
    """The typed endpoint or cache returned invalid/untrusted data."""


class QwenSystemOneBackend(Protocol):
    def score_relations(self, objective: str, relation_definitions: Mapping[str, str]) -> dict: ...


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ProtocolError(f"{name} must be finite numeric")
    return float(value)


def _text(value: Any, maximum: int, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"invalid {name}")
    if any(ord(c) < 32 for c in value):
        raise ValueError(f"control characters forbidden in {name}")
    # Defense in depth; the API admits abstract strings only, not a graph/context blob.
    if any(
        x in value.lower()
        for x in ('"coordinates"', '"geometry"', '"features"', "bearer ", "api_key", "authorization:")
    ):
        raise ValueError(f"non-abstract content forbidden in {name}")
    return value.strip()


def build_request(
    relations: Mapping[str, str], objective: str, *, permutations: int = 2, max_questions: int = 24
) -> dict:
    if not isinstance(relations, Mapping) or not 1 <= len(relations) <= max_questions <= 24:
        raise ValueError("relation batch must contain 1..24 abstract relation types")
    objective = _text(objective, 512, "objective")
    questions = {}
    for name in sorted(relations):
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,95}", name):
            raise ValueError("invalid relation identifier")
        description = _text(relations[name], 1024, "relation definition")
        questions[name] = {
            "type": "score",
            "criteria": list(CRITERIA),
            "instructions": f"Assess semantic relevance of relation {name}: {description}. "
            "Use the stated objective only. Do not infer delay, casualty, failure probability, "
            "road permissions, hazard perimeter or physical outcomes.",
        }
    if type(permutations) is not int or not 1 <= permutations <= 8:
        raise ValueError("permutations must be 1..8")
    return {
        "model": MODEL,
        "permutations": permutations,
        "state": {
            "task": "urban_dependency_retrieval",
            "objective": objective,
            "privacy": "Abstract relation types only; no coordinates, personal data or raw graph.",
        },
        "questions": questions,
    }


def parse_scores(response: Mapping[str, Any], expected_ids: set[str]) -> dict[str, float]:
    if not isinstance(response, Mapping):
        raise ProtocolError("response must be an object")
    answers = response.get("answers")
    if not isinstance(answers, dict) or set(answers) != expected_ids:
        raise ProtocolError("question set mismatch")
    keys = {"0", "1", "2"}
    result = {}
    for name, answer in answers.items():
        if not isinstance(answer, dict) or set(answer) != {
            "type",
            "score",
            "probabilities",
            "legend",
            "confidence",
        }:
            raise ProtocolError("unexpected answer fields; free text is forbidden")
        if answer["type"] != "score":
            raise ProtocolError("expected score answer")
        probabilities = answer["probabilities"]
        if not isinstance(probabilities, dict) or set(probabilities) != keys:
            raise ProtocolError("probability keys mismatch")
        p = {k: _number(v, "probability") for k, v in probabilities.items()}
        if any(x < 0 or x > 1 for x in p.values()) or abs(sum(p.values()) - 1) > 1e-6:
            raise ProtocolError("invalid probability distribution")
        score, confidence = _number(answer["score"], "score"), _number(answer["confidence"], "confidence")
        if not 0 <= score <= 2 or not 0 <= confidence <= 1:
            raise ProtocolError("score/confidence out of range")
        if abs(score - sum(int(k) * v for k, v in p.items())) > 1e-5:
            raise ProtocolError("score differs from rubric expectation")
        if answer["legend"] != dict(enumerate(CRITERIA)) and answer["legend"] != {
            str(i): c for i, c in enumerate(CRITERIA)
        }:
            raise ProtocolError("legend does not match requested rubric")
        result[name] = score / 2
    return result


def validate_endpoint(
    base_url: str, *, allow_remote_endpoint: bool = False, data_egress_scope: str = "none"
) -> tuple[str, str]:
    if not isinstance(base_url, str) or len(base_url) > 2048 or any(ord(c) < 33 for c in base_url):
        raise ValueError("invalid System-One endpoint")
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("endpoint requires HTTP(S), host and no URL credentials")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("endpoint must be a bare origin")
    try:
        port = parsed.port
        address = ipaddress.ip_address(parsed.hostname)
        local = address.is_loopback
    except ValueError:
        # Invalid port must not disappear into the hostname branch.
        port = parsed.port
        local = parsed.hostname == "localhost"
    if local:
        if data_egress_scope != "none":
            raise ValueError("loopback endpoint has data_egress_scope=none")
        if parsed.hostname == "localhost":
            addresses = socket.getaddrinfo(
                "localhost", port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM
            )
            if not addresses or any(not ipaddress.ip_address(x[4][0]).is_loopback for x in addresses):
                raise PermissionError("localhost must resolve exclusively to loopback")
        return base_url.rstrip("/") + "/v1/systemone", "none"
    if not allow_remote_endpoint or data_egress_scope not in {"organization_network", "external"}:
        raise PermissionError("non-loopback endpoint requires explicit permission and egress scope")
    if parsed.scheme != "https":
        raise PermissionError("remote System-One endpoints require TLS")
    return base_url.rstrip("/") + "/v1/systemone", data_egress_scope


@dataclass(frozen=True)
class BackendConfig:
    base_url: str = "http://127.0.0.1:8008"
    backend_revision: str = REFLEX_REVISION
    model_revision: str = MODEL_REVISION
    device: str | None = None
    dtype: str | None = None
    calibration_file: Path | None = None
    permutations: int = 2
    epsilon: float = 0.1
    max_questions: int = 24
    max_wall_ms: int = 5000
    max_response_bytes: int = 262144
    allow_remote_endpoint: bool = False
    data_egress_scope: str = "none"
    cache_dir: Path | None = None
    api_key: str | None = field(default=None, repr=False)

    def __post_init__(self):
        for revision in (self.backend_revision, self.model_revision):
            if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
                raise ValueError("exact 40-character backend/model revisions are required")
        for value, lo, hi in (
            (self.permutations, 1, 8),
            (self.max_questions, 1, 24),
            (self.max_wall_ms, 1, 120000),
            (self.max_response_bytes, 1024, 1048576),
        ):
            if type(value) is not int or not lo <= value <= hi:
                raise ValueError("invalid System-One runtime budget")
        if not 0 < _number(self.epsilon, "epsilon") <= 1:
            raise ValueError("epsilon out of range")
        if self.dtype not in {None, "float16", "bfloat16", "float32"}:
            raise ValueError("unsupported dtype")
        if self.device is not None and not re.fullmatch(r"(?:cpu|mps|cuda(?::[0-9]+)?)", self.device):
            raise ValueError("invalid device")
        if self.api_key is not None and (
            not isinstance(self.api_key, str) or any(ord(c) < 33 or ord(c) > 126 for c in self.api_key)
        ):
            raise ValueError("invalid credential encoding")
        validate_endpoint(
            self.base_url,
            allow_remote_endpoint=self.allow_remote_endpoint,
            data_egress_scope=self.data_egress_scope,
        )


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProtocolError("System-One redirects are forbidden")


def _strict_json(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ProtocolError("duplicate JSON key")
            result[k] = v
        return result

    def constant(_):
        raise ProtocolError("nonfinite JSON constant")

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError):
        raise ProtocolError("invalid typed JSON") from None
    if not isinstance(value, dict):
        raise ProtocolError("response must be an object")
    return value


class ReflexBackend:
    def __init__(self, config: BackendConfig | None = None):
        self.config = config or BackendConfig()
        self.endpoint, self.egress_scope = validate_endpoint(
            self.config.base_url,
            allow_remote_endpoint=self.config.allow_remote_endpoint,
            data_egress_scope=self.config.data_egress_scope,
        )
        self.last_provenance: dict = {}
        self._memory_cache: dict = {}
        self._calibration_hash = None
        if self.config.calibration_file is not None:
            path = Path(self.config.calibration_file)
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 1048576:
                raise ValueError("calibration must be a regular file of at most 1 MiB")
            self._calibration_hash = sha256(path.read_bytes()).hexdigest()

    def _request(self, payload: bytes) -> bytes:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if getattr(self.config, "user_agent", None):
            headers["User-Agent"] = self.config.user_agent
        if self.config.api_key:
            headers["Authorization"] = "Bearer " + self.config.api_key
        req = Request(self.endpoint, data=payload, headers=headers, method="POST")
        # Ignore process proxy variables: local/private inference must not leak to an HTTP proxy.
        opener = build_opener(ProxyHandler({}), _NoRedirect())
        deadline = time.monotonic() + self.config.max_wall_ms / 1000
        try:
            with opener.open(req, timeout=self.config.max_wall_ms / 1000) as stream:
                if stream.status != 200:
                    raise ProtocolError("unexpected System-One HTTP status")
                if stream.headers.get_content_type() != "application/json":
                    raise ProtocolError("System-One response must be JSON")
                parts, size = [], 0
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise BlockedEnvironment("System-One wall-time budget exhausted")
                    chunk = stream.read1(min(16384, self.config.max_response_bytes - size + 1))
                    if not chunk:
                        break
                    parts.append(chunk)
                    size += len(chunk)
                    if size > self.config.max_response_bytes:
                        raise ProtocolError("System-One response exceeds byte budget")
                if time.monotonic() > deadline:
                    raise BlockedEnvironment("System-One wall-time budget exhausted")
                return b"".join(parts)
        except HTTPError as exc:
            raise BlockedEnvironment(f"System-One HTTP {exc.code}; no fallback was used") from None
        except (URLError, TimeoutError, ConnectionError, OSError):
            raise BlockedEnvironment("System-One endpoint unavailable; no fallback was used") from None

    def _cache_path(self, key: str) -> Path | None:
        if self.config.cache_dir is None:
            return None
        root = Path(self.config.cache_dir)
        if root.is_symlink():
            raise ValueError("cache directory cannot be a symlink")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = root / (key + ".json")
        if path.is_symlink():
            raise ProtocolError("cache file cannot be a symlink")
        return path

    def score_relations(self, objective: str, relation_definitions: Mapping[str, str]) -> dict:
        req = build_request(
            relation_definitions,
            objective,
            permutations=self.config.permutations,
            max_questions=self.config.max_questions,
        )
        rubric_hash = _digest(
            {"version": RUBRIC_VERSION, "criteria": CRITERIA, "questions": req["questions"]}
        )
        context_hash = _digest(req["state"])
        identity = {
            "request": req,
            "backend_revision": self.config.backend_revision,
            "model_revision": self.config.model_revision,
            "calibration": self._calibration_hash,
            "dtype": self.config.dtype,
            "device": self.config.device,
            "endpoint": self.endpoint,
            "epsilon": self.config.epsilon,
        }
        key = _digest(identity)
        cache_path = self._cache_path(key)
        cached = self._memory_cache.get(key)
        if cached is None and cache_path and cache_path.exists():
            if cache_path.stat().st_size > self.config.max_response_bytes + 4096:
                raise ProtocolError("oversized cache entry")
            cached = _strict_json(cache_path.read_bytes())
        started = time.monotonic()
        cache_hit = cached is not None
        if cache_hit:
            if cached.get("key") != key or cached.get("response_hash") != _digest(cached.get("response")):
                raise ProtocolError("cache integrity mismatch")
            response = cached["response"]
        else:
            response = _strict_json(self._request(_canonical(req)))
        scores = parse_scores(response, set(req["questions"]))
        if response.get("model") != MODEL:
            raise ProtocolError("response model does not match pinned Qwen3.5-4B profile")
        usage = response.get("usage", {})
        if not isinstance(usage, dict):
            raise ProtocolError("invalid usage object")
        safe_usage = {}
        for name in ("input_tokens", "output_tokens"):
            value = usage.get(name)
            if value is not None and (type(value) is not int or value < 0):
                raise ProtocolError("invalid token usage")
            safe_usage[name] = value
        if safe_usage["output_tokens"] not in (0, None):
            raise ProtocolError("generative output is forbidden")
        safe_response = {"model": MODEL, "answers": response["answers"], "usage": safe_usage}
        if not cache_hit:
            cached = {"key": key, "response": safe_response, "response_hash": _digest(safe_response)}
            self._memory_cache[key] = copy.deepcopy(cached)
            if cache_path:
                fd, name = tempfile.mkstemp(prefix=".policy-", dir=cache_path.parent)
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(_canonical(cached))
                    os.replace(name, cache_path)
                finally:
                    if os.path.exists(name):
                        os.unlink(name)
        wall_ms = (time.monotonic() - started) * 1000
        self.last_provenance = {
            "cache_key": key,
            "cache_hit": cache_hit,
            "data_egress_scope": self.egress_scope,
            "request_sha256": sha256(_canonical(req)).hexdigest(),
            "response_sha256": _digest(safe_response),
            "runtime_pins_source": "deployment_configuration",
            "runtime_pins_independently_verified": False,
            "real_inference_this_call": not cache_hit,
            "release_gate_complete": False,
            "calibration_status": "provided_not_independently_validated"
            if self._calibration_hash
            else "NOT_CALIBRATED",
        }
        return {
            "schema_version": "1.1",
            "provider_mode": "replay" if cache_hit else "local_qwen",
            "requested_model": MODEL,
            "resolved_model": MODEL,
            "rubric_hash": rubric_hash,
            "context_hash": context_hash,
            "scores": scores,
            "epsilon": self.config.epsilon,
            "confidence_use": "diagnostic_only",
            "applied_transition_hash": None,
            "backend_impl": "reflex",
            "backend_revision": self.config.backend_revision,
            "model_revision": self.config.model_revision,
            "calibration_sha256": self._calibration_hash,
            "permutations": self.config.permutations,
            "dtype": self.config.dtype,
            "usage": {
                **safe_usage,
                "wall_ms": wall_ms,
                "questions": len(scores),
                "forward_passes": None,
                "device": self.config.device,
                "peak_memory_mb": None,
            },
        }
