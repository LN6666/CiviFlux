# Qwen-based Jev: Featherless SimpleJev

The selected product is **Featherless SimpleJev**, using `featherless-ai/Qwen3.8-27B-classifier`. It is distinct from TypeSafe's original closed Jev, Reflex, and ordinary Qwen chat-generated scores. No local model is deployed.

```python
from pathlib import Path
from adapters.system_one import SimpleJevBackend, SimpleJevConfig

backend = SimpleJevBackend(SimpleJevConfig.from_env(Path(".env")))
policy = backend.score_relations(
    "facility_access", {"ACCESS_FOR": "A road is on a verified access path to a facility."}
)
```

The [official SimpleJev API reference](https://simple-jev.featherless.ai/docs) documents these hosted endpoints:

| Mode | Origin and path | Authentication |
|---|---|---|
| `simplejev_demo` | `https://simple-jev-demo-api.featherless.ai/v1/classifier` | None; free public demo |
| `simplejev_api` | `https://api.featherless.ai/v1/classifier` | `FEATHERLESS_API_KEY` bearer token; paid access remains disabled |

The demo's `/v1/models` lists available model IDs. Its context limit is 2k tokens including server instructions and formatting; an 8 KiB client byte limit is **not** a guarantee of fitting that token limit. Our demo batch cap is six relation types. The [provider's Qwen tutorial](https://featherless.ai/blog/jev-llm-classifier-qwen3-simple-jev) identifies the Qwen3.8-27B classifier used here.

Requests contain only `model`, an abstract objective `state`, and typed relation `questions`. Each question uses `score`, instructions and three ordered relevance criteria. There is no chat completion, `temperature`, `max_tokens`, `stream`, image, raw city object, geometry or user note. The adapter checks the complete question set, finite normalized probabilities, exact legend, expected zero-based rubric score, and confidence equal to maximum level probability. It normalizes the score by dividing by two. These conditional scores are **not calibrated urban risk or correctness probabilities**.

## Authorization and reproducibility

Copy `.env.example` to gitignored `.env` only if configuration is needed. `SIMPLEJEV_ALLOW_EGRESS=0` and `SIMPLEJEV_MAX_CALLS=0` keep all calls disabled. A provided key alone never authorizes spending. The current user has deferred paid testing; no production request is authorized. A separately authorized bounded free-demo smoke uses an explicit budget ID and at most the authorized call count.

Every fresh request reserves an attempt in a locked persistent ledger before network access. Failed requests count, and the adapter never retries or changes providers. Endpoint/model changes require a new authorization ID. The demo never receives `FEATHERLESS_API_KEY`, even if one is configured. Redirects and process HTTP proxies are disabled; only the two HTTPS provider origins are accepted.

Cache identity includes ontology version, relation definitions, objective, rubric/prompt contract, model ID and client code revision. Hosted weight/server revisions remain unreported, so cross-deployment model drift cannot be guaranteed absent. `ontology_version` must be supplied from the authoritative ontology manifest by the application.

Content-addressed cache replay is labelled `replay`; a new request is labelled `simplejev_demo` or `simplejev_api`. Provenance keeps response/model/request hashes, token accounting, call budget and score semantics. Server commit, exact weights revision, precision and deployment calibration are not exposed by the hosted contract; they remain **unreported/unverified**, not invented pins. `usage.output_tokens` is implementation accounting and may be one per question; it is not treated as text generation or billed output. A typed response alone never completes graph application or urban evaluation gates.

`ReflexBackend` and `QwenAPIBackend` remain optional, separately named adapters. Their evidence cannot substitute for SimpleJev. The superseded `RemoteReflexBackend` was removed before deployment or network use.

## Recorded bounded verification

`evidence/wp3/simplejev_graph_integration.json` records three total free-demo attempts (first HTTP 403; two successful typed responses after setting a truthful CiviFlux User-Agent), zero paid calls, and offline cache application to toy and Helsinki graphs. Both graph runs preserve physical facts; mixed-relation baseline transition hashes change. Closed-seed event transition hashes do not change. This proves the protocol/application path, not calibrated probabilities or improved policy quality. `scripts/systemone_preflight.py` is offline by default and records `DEFERRED_USER` with default disabled configuration; `--live` still needs a separately authorized bounded configuration.
