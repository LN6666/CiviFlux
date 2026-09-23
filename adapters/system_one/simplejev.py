"""Featherless SimpleJev hosted typed classifier, distinct from chat generation.

No local model, tokenizer, weight download or cloud deployment. Requests disclose
only bounded abstract relation definitions and objectives. Demo and production
origins have separate scope-bound call authorizations; neither runs by default.
"""

from __future__ import annotations

import copy
import fcntl
import json
import os
import re
import tempfile
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

from .qwen_api import load_env_file
from .reflex import (
    CRITERIA,
    BlockedEnvironment,
    ProtocolError,
    ReflexBackend,
    _canonical,
    _digest,
    _number,
    _strict_json,
    build_request,
)

DEMO_BASE_URL = "https://simple-jev-demo-api.featherless.ai"
PRODUCTION_BASE_URL = "https://api.featherless.ai"
SIMPLEJEV_MODEL = "featherless-ai/Qwen3.8-27B-classifier"
SCORE_SEMANTICS = "simplejev_model_semantic_relevance_weight_not_calibrated_probability"
PROMPT_CONTRACT = "simplejev_shared_v1"
RUBRIC_VERSION = "urbanimpact-simplejev-relation-v1"
# Full API probabilities are checked numerically. Shortened prose examples in the
# provider blog are NOT wire fixtures and do not justify relaxing these tolerances.
PROBABILITY_TOLERANCE = 1e-6
EXPECTATION_TOLERANCE = 1e-5


def validate_endpoint(base_url: str) -> tuple[str, str]:
    if not isinstance(base_url, str) or len(base_url) > 2048 or any(ord(c) < 33 for c in base_url):
        raise ValueError("invalid SimpleJev origin")
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise PermissionError("SimpleJev requires HTTPS without URL credentials, query or fragment")
    if parsed.port not in (None, 443) or parsed.path not in ("", "/"):
        raise ValueError("SimpleJev base URL must be an official bare HTTPS origin")
    modes = {"simple-jev-demo-api.featherless.ai": "simplejev_demo", "api.featherless.ai": "simplejev_api"}
    mode = modes.get(parsed.hostname or "")
    if mode is None:
        raise PermissionError("SimpleJev host is outside the explicit provider allowlist")
    return base_url.rstrip("/") + "/v1/classifier", mode


@dataclass(frozen=True)
class SimpleJevConfig:
    base_url: str = DEMO_BASE_URL
    model: str = SIMPLEJEV_MODEL
    ontology_version: str = "1.0.0"
    api_key: str | None = field(default=None, repr=False)
    allow_egress: bool = False
    max_calls: int = 0
    budget_id: str = "unapproved"
    budget_ledger: Path = Path(".runtime/simplejev_budget.json")
    cache_dir: Path | None = Path(".runtime/simplejev_cache")
    max_questions: int = 6
    max_wall_ms: int = 45000
    max_request_bytes: int = 8192
    max_response_bytes: int = 262144
    epsilon: float = 0.1

    @property
    def provider_mode(self) -> str:
        return validate_endpoint(self.base_url)[1]

    @property
    def ready(self) -> bool:
        return (
            self.allow_egress
            and self.max_calls > 0
            and (self.provider_mode == "simplejev_demo" or bool(self.api_key))
        )

    def __post_init__(self):
        validate_endpoint(self.base_url)
        if not isinstance(self.ontology_version, str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]{1,96}", self.ontology_version
        ):
            raise ValueError("invalid ontology version")
        if not isinstance(self.model, str) or not re.fullmatch(
            r"featherless-ai/[A-Za-z0-9_.-]+-classifier", self.model
        ):
            raise ValueError("invalid SimpleJev classifier model identifier")
        if self.api_key is not None and (
            not isinstance(self.api_key, str)
            or not self.api_key
            or any(ord(c) < 33 or ord(c) > 126 for c in self.api_key)
        ):
            raise ValueError("invalid SimpleJev credential encoding")
        for value, lo, hi in (
            (self.max_calls, 0, 10000),
            (self.max_questions, 1, 24),
            (self.max_wall_ms, 1, 120000),
            (self.max_request_bytes, 1024, 65536),
            (self.max_response_bytes, 1024, 1048576),
        ):
            if type(value) is not int or not lo <= value <= hi:
                raise ValueError("invalid SimpleJev runtime/call budget")
        if self.provider_mode == "simplejev_demo" and self.max_questions > 6:
            raise ValueError("public-demo batches are conservatively limited to six questions")
        if not isinstance(self.budget_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,96}", self.budget_id):
            raise ValueError("invalid SimpleJev budget ID")
        if self.max_calls and self.budget_id == "unapproved":
            raise ValueError("explicit authorization ID required before remote calls")
        if not 0 < _number(self.epsilon, "epsilon") <= 1:
            raise ValueError("epsilon out of range")

    @classmethod
    def from_env(cls, env_file: Path | None = None, **overrides) -> SimpleJevConfig:
        env = load_env_file(env_file) if env_file else {}
        env.update(os.environ)
        args = {
            "base_url": env.get("SIMPLEJEV_BASE_URL") or DEMO_BASE_URL,
            "model": env.get("SIMPLEJEV_MODEL") or SIMPLEJEV_MODEL,
            "ontology_version": env.get("SIMPLEJEV_ONTOLOGY_VERSION") or "1.0.0",
            "api_key": env.get("FEATHERLESS_API_KEY") or None,
            "allow_egress": env.get("SIMPLEJEV_ALLOW_EGRESS") == "1",
            "max_calls": int(env.get("SIMPLEJEV_MAX_CALLS", "0")),
            "budget_id": env.get("SIMPLEJEV_BUDGET_ID", "unapproved"),
            "max_questions": int(env.get("SIMPLEJEV_MAX_QUESTIONS", "6")),
            "max_wall_ms": int(env.get("SIMPLEJEV_MAX_WALL_MS", "45000")),
        }
        args.update(overrides)
        return cls(**args)


def build_simplejev_request(objective: str, relations: Mapping[str, str], config: SimpleJevConfig) -> dict:
    # Reuse abstract-field validation, not the Reflex-specific model or extensions.
    checked = build_request(relations, objective, max_questions=config.max_questions)
    questions = {
        name: {
            "type": "score",
            "instructions": "Semantic relevance to the objective: "
            + relations[name]
            + ". Do not infer physical risk or travel time.",
            "criteria": list(CRITERIA),
        }
        for name in sorted(checked["questions"])
    }
    return {
        "model": config.model,
        "state": {
            "task": "urban_dependency_retrieval",
            "objective": checked["state"]["objective"],
            "ontology_version": config.ontology_version,
            "privacy": "Abstract ontology relations only; no city objects, geometry or personal data.",
        },
        "questions": questions,
    }


def parse_simplejev_scores(response: dict, expected_ids: set[str], model: str) -> tuple[dict, dict]:
    if not isinstance(response, dict) or response.get("model") != model:
        raise ProtocolError("SimpleJev returned a different model identifier")
    answers = response.get("answers")
    if not isinstance(answers, dict) or set(answers) != expected_ids:
        raise ProtocolError("SimpleJev question set mismatch")
    expected_legend = {str(i): label for i, label in enumerate(CRITERIA)}
    scores = {}
    for name, answer in answers.items():
        if (
            not isinstance(answer, dict)
            or set(answer) != {"type", "score", "confidence", "probabilities", "legend"}
            or answer.get("type") != "score"
        ):
            raise ProtocolError("SimpleJev must return typed score answers without free text")
        probabilities = answer["probabilities"]
        if not isinstance(probabilities, dict) or set(probabilities) != set(expected_legend):
            raise ProtocolError("SimpleJev rubric probability keys mismatch")
        p = {key: _number(value, "probability") for key, value in probabilities.items()}
        if any(v < 0 or v > 1 for v in p.values()) or abs(sum(p.values()) - 1) > PROBABILITY_TOLERANCE:
            raise ProtocolError("invalid SimpleJev conditional probability distribution")
        score = _number(answer["score"], "score")
        confidence = _number(answer["confidence"], "confidence")
        if not 0 <= score <= len(CRITERIA) - 1 or not 0 <= confidence <= 1:
            raise ProtocolError("SimpleJev score/confidence outside rubric range")
        if abs(score - sum(int(k) * v for k, v in p.items())) > EXPECTATION_TOLERANCE:
            raise ProtocolError("SimpleJev score differs from the expected zero-based rubric index")
        if abs(confidence - max(p.values())) > PROBABILITY_TOLERANCE:
            raise ProtocolError("SimpleJev confidence must equal maximum level probability")
        if answer["legend"] != expected_legend:
            raise ProtocolError("SimpleJev legend does not match the requested rubric")
        scores[name] = score / (len(CRITERIA) - 1)
    usage = response.get("usage", {})
    if not isinstance(usage, dict):
        raise ProtocolError("invalid SimpleJev usage object")
    safe_usage = {}
    for field_name in ("input_tokens", "output_tokens"):
        value = usage.get(field_name)
        if value is not None and (type(value) is not int or value < 0):
            raise ProtocolError("invalid SimpleJev implementation token accounting")
        safe_usage[field_name] = value
    # Hosted output accounting can be one token/question; it does not imply generation or billing.
    return scores, safe_usage


class SimpleJevBackend:
    def __init__(self, config: SimpleJevConfig | None = None):
        self.config = config or SimpleJevConfig.from_env()
        self.endpoint, self.provider_mode = validate_endpoint(self.config.base_url)
        self.last_provenance: dict = {}
        self.attempted_calls = 0
        self._client_revision = "client_sha256:" + sha256(Path(__file__).read_bytes()).hexdigest()
        self._cache: dict = {}
        self._lock = threading.Lock()

    def _reserve_call(self) -> int:
        if not self.config.allow_egress:
            raise BlockedEnvironment("BLOCKED_SIMPLEJEV_EGRESS: abstract relation egress not authorized")
        if not self.config.max_calls:
            raise BlockedEnvironment("BLOCKED_SIMPLEJEV_BUDGET: no remote calls authorized")
        if self.provider_mode == "simplejev_api" and not self.config.api_key:
            raise BlockedEnvironment("BLOCKED_SIMPLEJEV_CREDENTIALS: production requires FEATHERLESS_API_KEY")
        path = Path(self.config.budget_ledger)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "r+") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            raw = stream.read(65537)
            if len(raw) > 65536:
                raise PermissionError("SimpleJev budget ledger exceeds size limit")
            try:
                ledger = json.loads(raw) if raw else {}
            except ValueError:
                raise PermissionError("invalid SimpleJev budget ledger") from None
            if not isinstance(ledger, dict):
                raise PermissionError("invalid SimpleJev budget ledger")
            scope_hash = _digest(
                {"endpoint": self.endpoint, "model": self.config.model, "mode": self.provider_mode}
            )
            entry = ledger.get(
                self.config.budget_id,
                {"attempted_calls": 0, "max_calls": self.config.max_calls, "scope_hash": scope_hash},
            )
            if (
                not isinstance(entry, dict)
                or entry.get("max_calls") != self.config.max_calls
                or entry.get("scope_hash") != scope_hash
            ):
                raise PermissionError("provider/model/budget change requires a new explicit authorization ID")
            count = entry.get("attempted_calls")
            if type(count) is not int or count < 0:
                raise PermissionError("invalid SimpleJev attempt count")
            if count >= self.config.max_calls:
                raise BlockedEnvironment("BLOCKED_SIMPLEJEV_BUDGET: authorized call budget exhausted")
            count += 1
            ledger[self.config.budget_id] = {
                "attempted_calls": count,
                "max_calls": self.config.max_calls,
                "scope_hash": scope_hash,
                "last_attempt_at": datetime.now(UTC).isoformat(),
            }
            stream.seek(0)
            stream.truncate()
            json.dump(ledger, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
            return count

    def _request(self, payload: bytes) -> bytes:
        # Never send a production secret to the free demonstration host.
        transport = SimpleNamespace(
            endpoint=self.endpoint,
            config=SimpleNamespace(
                api_key=self.config.api_key if self.provider_mode == "simplejev_api" else None,
                max_wall_ms=self.config.max_wall_ms,
                max_response_bytes=self.config.max_response_bytes,
                user_agent="CiviFlux/0.1 SimpleJevAdapter/1.0",
            ),
        )
        return ReflexBackend._request(transport, payload)

    def score_relations(self, objective: str, relation_definitions: Mapping[str, str]) -> dict:
        request = build_simplejev_request(objective, relation_definitions, self.config)
        payload = _canonical(request)
        if len(payload) > self.config.max_request_bytes:
            raise ValueError("SimpleJev abstract request exceeds the byte budget")
        rubric_hash = _digest({"version": RUBRIC_VERSION, "questions": request["questions"]})
        key = _digest(
            {
                "request": request,
                "endpoint": self.endpoint,
                "rubric_version": RUBRIC_VERSION,
                "epsilon": self.config.epsilon,
                "prompt_contract": PROMPT_CONTRACT,
                "ontology_version": self.config.ontology_version,
                "client_revision": self._client_revision,
                "server_build": "unreported",
                "weights_revision": "unreported",
            }
        )
        path = None
        if self.config.cache_dir:
            root = Path(self.config.cache_dir)
            if root.is_symlink():
                raise PermissionError("SimpleJev cache directory cannot be a symlink")
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = root / (key + ".json")
            if path.is_symlink():
                raise PermissionError("SimpleJev cache file cannot be a symlink")
        started = time.monotonic()
        with self._lock:
            entry = self._cache.get(key)
            if entry is None and path and path.exists():
                if path.stat().st_size > self.config.max_response_bytes + 4096:
                    raise ProtocolError("oversized SimpleJev cache")
                entry = _strict_json(path.read_bytes())
            hit = entry is not None
            attempt = None
            if hit:
                if entry.get("key") != key or entry.get("response_sha256") != _digest(entry.get("response")):
                    raise ProtocolError("SimpleJev cache integrity mismatch")
                response = entry["response"]
                wire_hash = entry.get("wire_response_sha256")
            else:
                attempt = self._reserve_call()
                self.attempted_calls += 1
                raw = self._request(payload)
                wire_hash = sha256(raw).hexdigest()
                response = _strict_json(raw)
            scores, usage = parse_simplejev_scores(response, set(relation_definitions), self.config.model)
            safe_response = {"model": response["model"], "answers": response["answers"], "usage": usage}
            if not hit:
                entry = {
                    "key": key,
                    "response": safe_response,
                    "response_sha256": _digest(safe_response),
                    "wire_response_sha256": wire_hash,
                }
                self._cache[key] = copy.deepcopy(entry)
                if path:
                    fd, temporary = tempfile.mkstemp(prefix=".simplejev-", dir=path.parent)
                    try:
                        with os.fdopen(fd, "wb") as stream:
                            stream.write(_canonical(entry))
                        os.replace(temporary, path)
                    finally:
                        if os.path.exists(temporary):
                            os.unlink(temporary)
        self.last_provenance = {
            "provider": "Featherless SimpleJev",
            "provider_mode": self.provider_mode,
            "endpoint_host": urlsplit(self.endpoint).hostname,
            "score_semantics": SCORE_SEMANTICS,
            "prompt_contract": PROMPT_CONTRACT,
            "ontology_version": self.config.ontology_version,
            "client_revision": self._client_revision,
            "hosted_version_drift_guarantee": "UNAVAILABLE_WITHOUT_SERVER_VERSION",
            "data_egress_scope": "external_abstract_relation_definitions_only",
            "requested_model": self.config.model,
            "resolved_model": response["model"],
            "weights_revision": "NOT_REPORTED_BY_HOSTED_API",
            "server_revision": "NOT_REPORTED_BY_HOSTED_API",
            "runtime_pins_independently_verified": False,
            "calibration_status": "NOT_CALIBRATED_FOR_URBAN_RELATIONS",
            "cache_hit": hit,
            "cache_key": key,
            "remote_call_this_run": not hit,
            "request_sha256": sha256(payload).hexdigest(),
            "wire_response_sha256": wire_hash,
            "response_sha256": _digest(safe_response),
            "budget_id": self.config.budget_id,
            "attempt_number": attempt,
            "authorized_max_calls": self.config.max_calls,
            "usage_semantics": "implementation_accounting_not_billing",
            "paid_call_this_run": not hit and self.provider_mode == "simplejev_api",
            "local_model_deployed": False,
            "ordinary_chat_fallback": False,
            "release_gate_complete": False,
        }
        return {
            "schema_version": "1.1",
            "provider_mode": "replay" if hit else self.provider_mode,
            "requested_model": self.config.model,
            "resolved_model": response["model"],
            "rubric_hash": rubric_hash,
            "context_hash": _digest(request["state"]),
            "scores": scores,
            "epsilon": self.config.epsilon,
            "confidence_use": "diagnostic_only",
            "applied_transition_hash": None,
            "backend_impl": "featherless_simplejev_classifier",
            "backend_revision": self._client_revision,
            "model_revision": "provider_model_id:" + response["model"] + ";weights_revision_unreported",
            "calibration_sha256": None,
            "permutations": 1,
            "dtype": None,
            "usage": {
                **usage,
                "wall_ms": (time.monotonic() - started) * 1000,
                "questions": len(scores),
                "forward_passes": None,
                "device": "provider_managed_unreported",
                "peak_memory_mb": None,
            },
        }
