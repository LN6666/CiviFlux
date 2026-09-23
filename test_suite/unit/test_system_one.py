"""Transport and contract unit tests. Every HTTP response here is a TEST DOUBLE.

These tests cannot satisfy real Qwen or release integration gates.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from jsonschema import validate

from adapters.system_one import (
    BackendConfig,
    BlockedEnvironment,
    ProtocolError,
    ReflexBackend,
    build_request,
    parse_scores,
    validate_endpoint,
)
from adapters.system_one.reflex import CRITERIA, MODEL


def response():
    return {
        "model": MODEL,
        "answers": {
            "ACCESS_FOR": {
                "type": "score",
                "score": 1.75,
                "confidence": 0.8,
                "probabilities": {"0": 0.05, "1": 0.15, "2": 0.8},
                "legend": {str(i): x for i, x in enumerate(CRITERIA)},
            }
        },
        "usage": {"input_tokens": 20, "output_tokens": 0},
    }


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        request_count = 0
        last_payload = None
        last_auth = None
        body = response()
        status = 200
        delay = 0

        def log_message(self, *_):
            pass

        def do_POST(self):
            type(self).request_count += 1
            type(self).last_payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            type(self).last_auth = self.headers.get("Authorization")
            time.sleep(self.delay)
            self.send_response(self.status)
            self.send_header("Content-Type", "application/json")
            if self.status == 302:
                self.send_header("Location", "http://example.invalid/exfiltrate")
            self.end_headers()
            try:
                self.wfile.write(json.dumps(self.body).encode())
            except BrokenPipeError:
                pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield f"http://127.0.0.1:{srv.server_port}", Handler
    srv.shutdown()
    srv.server_close()
    th.join()


def test_schema_cache_and_no_raw_city_content(server, tmp_path, monkeypatch):
    url, handler = server
    monkeypatch.setenv("http_proxy", "http://example.invalid:90")
    config = BackendConfig(base_url=url, cache_dir=tmp_path, api_key="unit-secret")
    backend = ReflexBackend(config)
    policy = backend.score_relations("facility_access", {"ACCESS_FOR": "a road accesses a facility"})
    validate(policy, json.loads(Path("contracts/policy.schema.json").read_text()))
    assert policy["scores"] == {"ACCESS_FOR": 0.875}
    assert policy["provider_mode"] == "local_qwen"  # transport mode, NOT a live gate assertion
    assert handler.last_auth == "Bearer unit-secret"
    assert set(handler.last_payload["state"]) == {"objective", "privacy", "task"}
    assert not backend.last_provenance["release_gate_complete"]
    policy["scores"]["ACCESS_FOR"] = 0
    replay = backend.score_relations("facility_access", {"ACCESS_FOR": "a road accesses a facility"})
    assert replay["provider_mode"] == "replay" and replay["scores"]["ACCESS_FOR"] == 0.875
    assert handler.request_count == 1
    restarted = ReflexBackend(config)
    assert (
        restarted.score_relations("facility_access", {"ACCESS_FOR": "a road accesses a facility"})[
            "provider_mode"
        ]
        == "replay"
    )
    assert handler.request_count == 1
    saved = next(tmp_path.glob("*.json")).read_text()
    assert "unit-secret" not in saved and "a road accesses" not in saved
    assert "unit-secret" not in repr(config)
    assert not restarted.last_provenance["real_inference_this_call"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("score", 1.2),
        ("score", True),
        ("confidence", float("nan")),
        ("confidence", -1),
        ("type", "choice"),
        ("legend", {"0": "Wrong"}),
    ],
)
def test_reject_invalid_answer(field, value):
    payload = response()
    payload["answers"]["ACCESS_FOR"][field] = value
    with pytest.raises(ProtocolError):
        parse_scores(payload, {"ACCESS_FOR"})


@pytest.mark.parametrize(
    "probabilities",
    [
        {"0": 0.1, "1": 0.1, "2": 0.1},
        {"0": -0.1, "1": 0.3, "2": 0.8},
        {"0": False, "1": 0.2, "2": 0.8},
        {"0": 0, "1": 0},
        {"0": float("inf"), "1": 0, "2": 0},
    ],
)
def test_reject_probabilities(probabilities):
    payload = response()
    payload["answers"]["ACCESS_FOR"]["probabilities"] = probabilities
    with pytest.raises(ProtocolError):
        parse_scores(payload, {"ACCESS_FOR"})


def test_reject_extra_question_or_free_text():
    with pytest.raises(ProtocolError):
        parse_scores(response(), {"OTHER"})
    payload = response()
    payload["answers"]["ACCESS_FOR"]["reasoning"] = "The road is safe"
    with pytest.raises(ProtocolError):
        parse_scores(payload, {"ACCESS_FOR"})


@pytest.mark.parametrize(
    "url",
    [
        "ftp://localhost",
        "http://user:secret@localhost",
        "http://localhost/path",
        "http://localhost?key=x",
        "http://localhost#fragment",
        "http://localhost:bad",
    ],
)
def test_reject_bad_endpoint(url):
    with pytest.raises(ValueError):
        validate_endpoint(url)


def test_remote_requires_explicit_permission_and_scope():
    with pytest.raises(PermissionError):
        validate_endpoint("https://example.org")
    with pytest.raises(PermissionError):
        validate_endpoint("https://example.org", allow_remote_endpoint=True)
    with pytest.raises(PermissionError):
        validate_endpoint("http://example.org", allow_remote_endpoint=True, data_egress_scope="external")
    assert (
        validate_endpoint("https://example.org", allow_remote_endpoint=True, data_egress_scope="external")[1]
        == "external"
    )
    assert validate_endpoint("http://[::1]:8008")[1] == "none"


@pytest.mark.parametrize(
    "relations,objective",
    [
        ({}, "x"),
        ({"X": "x"}, ""),
        ({"X": {"geometry": [1, 2]}}, "x"),
        ({"X": '"coordinates": [60,24]'}, "x"),
        ({"bad id": "x"}, "x"),
        ({"X": "x"}, "x" * 513),
        ({f"R{i}": "x" for i in range(25)}, "x"),
    ],
)
def test_request_privacy_and_limits(relations, objective):
    with pytest.raises(ValueError):
        build_request(relations, objective)


def test_cache_key_covers_objective_semantics_permutations_precision_calibration(server, tmp_path):
    url, handler = server
    for kwargs, objective, desc in [
        ({}, "facility_access", "access"),
        ({}, "road_access", "access"),
        ({}, "facility_access", "different definition"),
        ({"permutations": 1}, "facility_access", "access"),
        ({"dtype": "float16"}, "facility_access", "access"),
    ]:
        ReflexBackend(BackendConfig(base_url=url, cache_dir=tmp_path, **kwargs)).score_relations(
            objective, {"ACCESS_FOR": desc}
        )
    calibration = tmp_path / "calibration"
    calibration.write_text('{"temperature":1}')
    ReflexBackend(
        BackendConfig(base_url=url, cache_dir=tmp_path, calibration_file=calibration)
    ).score_relations("facility_access", {"ACCESS_FOR": "access"})
    assert handler.request_count == 6


def test_cache_tampering_rejected(server, tmp_path):
    url, _ = server
    config = BackendConfig(base_url=url, cache_dir=tmp_path)
    ReflexBackend(config).score_relations("facility_access", {"ACCESS_FOR": "access"})
    path = next(tmp_path.glob("*.json"))
    data = json.loads(path.read_text())
    data["response"]["answers"]["ACCESS_FOR"]["score"] = 0
    path.write_text(json.dumps(data))
    with pytest.raises(ProtocolError):
        ReflexBackend(config).score_relations("facility_access", {"ACCESS_FOR": "access"})


def test_redirect_timeout_error_and_size_are_fail_closed(server):
    url, handler = server
    handler.status = 302
    with pytest.raises(ProtocolError):
        ReflexBackend(BackendConfig(base_url=url)).score_relations("access", {"ACCESS_FOR": "access"})
    handler.status = 503
    with pytest.raises(BlockedEnvironment, match="503"):
        ReflexBackend(BackendConfig(base_url=url)).score_relations("access", {"ACCESS_FOR": "access"})
    handler.status = 200
    handler.body = {"oversized": "x" * 2000}
    with pytest.raises(ProtocolError, match="byte budget"):
        ReflexBackend(BackendConfig(base_url=url, max_response_bytes=1024)).score_relations(
            "access", {"ACCESS_FOR": "access"}
        )
    handler.delay = 0.1
    with pytest.raises(BlockedEnvironment):
        ReflexBackend(BackendConfig(base_url=url, max_wall_ms=20)).score_relations(
            "access", {"ACCESS_FOR": "access"}
        )


def test_wrong_model_and_generated_output_rejected(server):
    url, handler = server
    handler.body["model"] = "some-other-model"
    with pytest.raises(ProtocolError, match="model"):
        ReflexBackend(BackendConfig(base_url=url)).score_relations("access", {"ACCESS_FOR": "access"})
    handler.body = response()
    handler.body["usage"]["output_tokens"] = 3
    with pytest.raises(ProtocolError, match="generative"):
        ReflexBackend(BackendConfig(base_url=url)).score_relations("access", {"ACCESS_FOR": "access"})


# Optional ordinary Qwen chat API comparison. These responses are test doubles;
# this adapter does not satisfy the selected SimpleJev integration.
from adapters.system_one import SCORE_SEMANTICS, QwenAPIBackend, QwenAPIConfig, load_env_file
from adapters.system_one.qwen_api import (
    DEFAULT_API_MODEL,
    parse_api_scores,
    validate_api_endpoint,
)


def api_response(scores=None):
    return {
        "model": DEFAULT_API_MODEL,
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": json.dumps({"scores": scores or {"ACCESS_FOR": 0.9}})},
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 20, "total_tokens": 140},
    }


def api_config(tmp_path, **overrides):
    options = {
        "api_key": "test-secret",
        "allow_egress": True,
        "max_calls": 2,
        "budget_id": "unit-test",
        "budget_ledger": tmp_path / "budget.json",
        "cache_dir": tmp_path / "cache",
    }
    options.update(overrides)
    return QwenAPIConfig(**options)


def test_api_schema_cache_budget_and_score_semantics(tmp_path, monkeypatch):
    calls = []

    def send(self, payload):
        calls.append(json.loads(payload))
        return json.dumps(api_response()).encode()

    monkeypatch.setattr(QwenAPIBackend, "_request", send)
    config = api_config(tmp_path)
    backend = QwenAPIBackend(config)
    policy = backend.score_relations("facility_access", {"ACCESS_FOR": "a road accesses a facility"})
    validate(policy, json.loads(Path("contracts/policy.schema.json").read_text()))
    assert policy["provider_mode"] == "qwen_api" and policy["scores"]["ACCESS_FOR"] == 0.9
    assert backend.last_provenance["score_semantics"] == SCORE_SEMANTICS
    assert "probabilities" not in json.dumps(calls[0]["response_format"])
    assert calls[0]["response_format"]["json_schema"]["strict"] is True
    assert calls[0]["max_tokens"] == 512 and calls[0]["enable_thinking"] is False
    assert (
        backend.score_relations("facility_access", {"ACCESS_FOR": "a road accesses a facility"})[
            "provider_mode"
        ]
        == "replay"
    )
    assert (
        QwenAPIBackend(config).score_relations(
            "facility_access", {"ACCESS_FOR": "a road accesses a facility"}
        )["provider_mode"]
        == "replay"
    )
    assert len(calls) == 1
    assert json.loads(config.budget_ledger.read_text())["unit-test"]["attempted_calls"] == 1
    assert "test-secret" not in repr(config)
    for path in tmp_path.rglob("*.json"):
        assert "test-secret" not in path.read_text()


@pytest.mark.parametrize(
    "override,error",
    [({"api_key": None}, "CREDENTIALS"), ({"allow_egress": False}, "EGRESS"), ({"max_calls": 0}, "BUDGET")],
)
def test_api_no_calls_without_explicit_key_egress_and_budget(tmp_path, monkeypatch, override, error):
    def forbidden(*_):
        raise AssertionError("network must not be called")

    monkeypatch.setattr(QwenAPIBackend, "_request", forbidden)
    with pytest.raises(BlockedEnvironment, match=error):
        QwenAPIBackend(api_config(tmp_path, **override)).score_relations("access", {"ACCESS_FOR": "access"})


def test_api_failed_attempts_count_and_no_retry(tmp_path, monkeypatch):
    attempts = []

    def fail(*_):
        attempts.append(1)
        raise BlockedEnvironment("network unavailable")

    monkeypatch.setattr(QwenAPIBackend, "_request", fail)
    config = api_config(tmp_path, max_calls=1)
    with pytest.raises(BlockedEnvironment, match="network"):
        QwenAPIBackend(config).score_relations("access", {"ACCESS_FOR": "access"})
    with pytest.raises(BlockedEnvironment, match="exhausted"):
        QwenAPIBackend(config).score_relations("access", {"ACCESS_FOR": "access"})
    assert len(attempts) == 1


@pytest.mark.parametrize(
    "scores",
    [
        {"ACCESS_FOR": True},
        {"ACCESS_FOR": -1},
        {"ACCESS_FOR": 1.01},
        {"ACCESS_FOR": float("nan")},
        {"OTHER": 0.9},
        {"ACCESS_FOR": 0.9, "OTHER": 0.2},
    ],
)
def test_api_reject_bad_scores(scores):
    with pytest.raises(ProtocolError):
        parse_api_scores(api_response(scores), {"ACCESS_FOR"}, DEFAULT_API_MODEL)


def test_api_refusal_truncation_and_free_text_rejected():
    raw = api_response()
    raw["choices"][0]["finish_reason"] = "length"
    with pytest.raises(ProtocolError):
        parse_api_scores(raw, {"ACCESS_FOR"}, DEFAULT_API_MODEL)
    raw = api_response()
    raw["choices"][0]["message"]["refusal"] = "cannot answer"
    with pytest.raises(ProtocolError):
        parse_api_scores(raw, {"ACCESS_FOR"}, DEFAULT_API_MODEL)
    raw = api_response()
    raw["choices"][0]["message"]["content"] = '```json\n{"scores":{"ACCESS_FOR":1}}\n```'
    with pytest.raises(ProtocolError):
        parse_api_scores(raw, {"ACCESS_FOR"}, DEFAULT_API_MODEL)
    raw = api_response()
    raw["choices"][0]["message"]["content"] = '{"scores":{"ACCESS_FOR":1},"speed":99}'
    with pytest.raises(ProtocolError):
        parse_api_scores(raw, {"ACCESS_FOR"}, DEFAULT_API_MODEL)
    raw = api_response()
    raw["usage"]["total_tokens"] = 0
    with pytest.raises(ProtocolError):
        parse_api_scores(raw, {"ACCESS_FOR"}, DEFAULT_API_MODEL)


def test_api_endpoint_allowlist():
    assert validate_api_endpoint("https://dashscope-intl.aliyuncs.com/compatible-mode/v1").endswith(
        "/chat/completions"
    )
    assert validate_api_endpoint("https://llm-workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1")
    for url in [
        "http://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "https://dashscope-intl.aliyuncs.com.evil.org/compatible-mode/v1",
        "https://user:secret@dashscope-intl.aliyuncs.com/compatible-mode/v1",
    ]:
        with pytest.raises(PermissionError):
            validate_api_endpoint(url)


def test_literal_env_load_never_executes(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('DASHSCOPE_API_KEY="test-local-secret"\nQWEN_API_MAX_CALLS=0\n')
    assert load_env_file(env)["DASHSCOPE_API_KEY"] == "test-local-secret"
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    assert "test-local-secret" not in repr(QwenAPIConfig.from_env(env))
    env.write_text("DASHSCOPE_API_KEY=$(touch /tmp/never-execute-civiflux)\n")
    with pytest.raises(ValueError):
        load_env_file(env)


def test_api_preflight_is_offline(tmp_path, monkeypatch):
    from scripts.systemone_preflight import preflight

    def forbidden(*_):
        raise AssertionError("preflight must not call network")

    monkeypatch.setattr(SimpleJevBackend, "_request", forbidden)
    report = preflight(SimpleJevConfig())
    assert report["status"] == "DEFERRED_USER"
    assert report["provider_mode"] == "simplejev_demo"
    assert report["credentials_required"] is False
    assert report["live_api_calls_performed"] == 0
    assert report["local_models_launched"] is False


def test_empty_env_key_is_reported_as_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    path = tmp_path / ".env"
    path.write_text("DASHSCOPE_API_KEY=\n")
    assert QwenAPIConfig.from_env(path).api_key is None


# The user's identified Qwen-based Jev product is Featherless SimpleJev.
from adapters.system_one import SimpleJevBackend, SimpleJevConfig
from adapters.system_one.simplejev import (
    DEMO_BASE_URL,
    PRODUCTION_BASE_URL,
    SIMPLEJEV_MODEL,
    build_simplejev_request,
    parse_simplejev_scores,
)
from adapters.system_one.simplejev import (
    validate_endpoint as validate_simplejev_endpoint,
)


def simplejev_response():
    value = response()
    value["model"] = SIMPLEJEV_MODEL
    value["usage"] = {"input_tokens": 230, "output_tokens": 1}
    return value


def simplejev_config(tmp_path, **overrides):
    options = {
        "allow_egress": True,
        "max_calls": 2,
        "budget_id": "simplejev-unit-test",
        "cache_dir": tmp_path / "cache",
        "budget_ledger": tmp_path / "budget.json",
    }
    options.update(overrides)
    return SimpleJevConfig(**options)


def test_simplejev_demo_schema_cache_and_usage_are_not_billing(tmp_path, monkeypatch):
    requests = []

    def send(_self, payload):
        requests.append(json.loads(payload))
        return json.dumps(simplejev_response()).encode()

    monkeypatch.setattr(SimpleJevBackend, "_request", send)
    config = simplejev_config(tmp_path)
    backend = SimpleJevBackend(config)
    policy = backend.score_relations("facility_access", {"ACCESS_FOR": "A road accesses a facility"})
    validate(policy, json.loads(Path("contracts/policy.schema.json").read_text()))
    assert policy["provider_mode"] == "simplejev_demo" and policy["scores"] == {"ACCESS_FOR": 0.875}
    assert policy["usage"]["output_tokens"] == 1
    assert backend.last_provenance["usage_semantics"] == "implementation_accounting_not_billing"
    assert not backend.last_provenance["paid_call_this_run"]
    assert not backend.last_provenance["runtime_pins_independently_verified"]
    assert not backend.last_provenance["release_gate_complete"]
    assert backend.last_provenance["response_freshness"] == "live_provider_response"
    captured_at = backend.last_provenance["response_captured_at"]
    assert set(requests[0]) == {"model", "state", "questions"}
    assert requests[0]["model"] == SIMPLEJEV_MODEL
    assert config.ready
    replay_backend = SimpleJevBackend(config)
    replay = replay_backend.score_relations("facility_access", {"ACCESS_FOR": "A road accesses a facility"})
    assert replay["provider_mode"] == "replay" and len(requests) == 1
    assert replay_backend.last_provenance["response_freshness"] == "frozen_replay_not_current_provider"
    assert replay_backend.last_provenance["response_captured_at"] == captured_at
    assert not replay_backend.last_provenance["remote_call_this_run"]
    assert json.loads(config.budget_ledger.read_text())[config.budget_id]["attempted_calls"] == 1


def test_simplejev_demo_never_sends_production_secret(tmp_path, monkeypatch):
    keys = []

    def transport(self, _payload):
        keys.append(self.config.api_key)
        return json.dumps(simplejev_response()).encode()

    monkeypatch.setattr(ReflexBackend, "_request", transport)
    config = simplejev_config(tmp_path, api_key="production-secret-not-for-demo")
    SimpleJevBackend(config).score_relations("access", {"ACCESS_FOR": "access"})
    assert keys == [None]
    for path in tmp_path.rglob("*.json"):
        assert "production-secret-not-for-demo" not in path.read_text()
    assert "production-secret-not-for-demo" not in repr(config)


def test_simplejev_paid_requires_key_and_separate_authorization_scope(tmp_path, monkeypatch):
    config = simplejev_config(tmp_path, base_url=PRODUCTION_BASE_URL)
    assert not config.ready
    with pytest.raises(BlockedEnvironment, match="CREDENTIALS"):
        SimpleJevBackend(config).score_relations("access", {"ACCESS_FOR": "access"})
    keys = []

    def transport(self, _payload):
        keys.append(self.config.api_key)
        return json.dumps(simplejev_response()).encode()

    monkeypatch.setattr(ReflexBackend, "_request", transport)
    SimpleJevBackend(simplejev_config(tmp_path)).score_relations("access", {"ACCESS_FOR": "access"})
    with pytest.raises(PermissionError, match="authorization"):
        SimpleJevBackend(
            simplejev_config(tmp_path, base_url=PRODUCTION_BASE_URL, api_key="unit-key")
        ).score_relations("access", {"ACCESS_FOR": "access"})
    paid = SimpleJevBackend(
        simplejev_config(
            tmp_path,
            base_url=PRODUCTION_BASE_URL,
            api_key="unit-key",
            budget_id="separate-production-authorization",
        )
    )
    policy = paid.score_relations("access", {"ACCESS_FOR": "access"})
    assert policy["provider_mode"] == "simplejev_api" and keys == [None, "unit-key"]


@pytest.mark.parametrize(
    "overrides,match", [({"allow_egress": False}, "EGRESS"), ({"max_calls": 0}, "BUDGET")]
)
def test_simplejev_no_call_without_authorization(tmp_path, monkeypatch, overrides, match):
    def forbidden(*_):
        raise AssertionError("network must not run")

    monkeypatch.setattr(SimpleJevBackend, "_request", forbidden)
    with pytest.raises(BlockedEnvironment, match=match):
        SimpleJevBackend(simplejev_config(tmp_path, **overrides)).score_relations(
            "access", {"ACCESS_FOR": "access"}
        )


def test_simplejev_error_counts_and_never_retries(tmp_path, monkeypatch):
    calls = []

    def fail(*_):
        calls.append(1)
        raise BlockedEnvironment("provider unavailable")

    monkeypatch.setattr(SimpleJevBackend, "_request", fail)
    config = simplejev_config(tmp_path, max_calls=1)
    with pytest.raises(BlockedEnvironment, match="unavailable"):
        SimpleJevBackend(config).score_relations("access", {"ACCESS_FOR": "access"})
    with pytest.raises(BlockedEnvironment, match="exhausted"):
        SimpleJevBackend(config).score_relations("access", {"ACCESS_FOR": "access"})
    assert calls == [1]


@pytest.mark.parametrize(
    "field,value",
    [
        ("score", 1.5),
        ("confidence", 0.61),
        ("score", True),
        ("confidence", float("nan")),
        ("legend", {"0": "Different"}),
        ("type", "choice"),
    ],
)
def test_simplejev_strict_typed_expectation_and_confidence(field, value):
    data = simplejev_response()
    data["answers"]["ACCESS_FOR"][field] = value
    with pytest.raises(ProtocolError):
        parse_simplejev_scores(data, {"ACCESS_FOR"}, SIMPLEJEV_MODEL)


def test_simplejev_rejects_ordinary_chat_and_wrong_model():
    with pytest.raises(ProtocolError):
        parse_simplejev_scores(api_response(), {"ACCESS_FOR"}, SIMPLEJEV_MODEL)
    data = simplejev_response()
    data["model"] = "Qwen/Qwen3.5-4B"
    with pytest.raises(ProtocolError):
        parse_simplejev_scores(data, {"ACCESS_FOR"}, SIMPLEJEV_MODEL)


def test_simplejev_endpoint_allowlist_and_demo_batch_limit():
    assert validate_simplejev_endpoint(DEMO_BASE_URL) == (DEMO_BASE_URL + "/v1/classifier", "simplejev_demo")
    for url in [
        "http://simple-jev-demo-api.featherless.ai",
        "https://simple-jev-demo-api.featherless.ai.evil.org",
        "https://key:secret@api.featherless.ai",
    ]:
        with pytest.raises(PermissionError):
            validate_simplejev_endpoint(url)
    with pytest.raises(ValueError):
        SimpleJevConfig(max_questions=7)
    with pytest.raises(ValueError, match="selected Qwen classifier"):
        SimpleJevConfig(model="featherless-ai/Other-classifier")
    with pytest.raises(ValueError):
        build_simplejev_request("access", {"X": '"geometry": [1, 2]'}, SimpleJevConfig())


def test_simplejev_cache_binds_ontology_definitions_objective_and_code_version(tmp_path, monkeypatch):
    calls = []

    def send(_self, payload):
        calls.append(json.loads(payload))
        return json.dumps(simplejev_response()).encode()

    monkeypatch.setattr(SimpleJevBackend, "_request", send)
    for version, objective, description in [
        ("1.0.0", "access", "access"),
        ("1.1.0", "access", "access"),
        ("1.0.0", "transit", "access"),
        ("1.0.0", "access", "different semantics"),
    ]:
        backend = SimpleJevBackend(simplejev_config(tmp_path, max_calls=5, ontology_version=version))
        backend.score_relations(objective, {"ACCESS_FOR": description})
        assert backend.last_provenance["ontology_version"] == version
        assert backend.last_provenance["client_revision"].startswith("client_sha256:")
    backend = SimpleJevBackend(simplejev_config(tmp_path, max_calls=5))
    backend._client_revision = "changed-client-version-for-cache-test"
    backend.score_relations("access", {"ACCESS_FOR": "access"})
    assert len(calls) == 5
    assert calls[1]["state"]["ontology_version"] == "1.1.0"


def test_simplejev_shared_contract_change_invalidates_cached_answer(tmp_path, monkeypatch):
    calls = []

    def send(_self, payload):
        calls.append(json.loads(payload))
        return json.dumps(simplejev_response()).encode()

    monkeypatch.setattr(SimpleJevBackend, "_request", send)
    config = simplejev_config(tmp_path)
    first = SimpleJevBackend(config)
    first.score_relations("access", {"ACCESS_FOR": "access"})
    first_revision = first.last_provenance["client_revision"]

    original_read = Path.read_bytes

    def changed_helper_read(path):
        content = original_read(path)
        return content + b"\n# changed shared contract\n" if path.name == "reflex.py" else content

    monkeypatch.setattr(Path, "read_bytes", changed_helper_read)
    second = SimpleJevBackend(config)
    second.score_relations("access", {"ACCESS_FOR": "access"})
    assert second.last_provenance["client_revision"] != first_revision
    assert not second.last_provenance["cache_hit"]
    assert len(calls) == 2
