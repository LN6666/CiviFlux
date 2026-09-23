# ADR 0001 — Data-local GIS core with explicit scenario and provider boundaries

Status: implemented direction with focused local checks passing; final release acceptance remains subject to `execution/STATE.md` and required gates. Updated 2026-09-24. Scope: Road & Fire GIS v1.

## Context

The engineering pack requires an embeddable Web GIS, local city-data processing, typed operational ontology and paired physical/semantic analysis. The user-designated remote System-One service is Featherless SimpleJev with its Qwen classifier. Neither the original local Reflex deployment nor ordinary Qwen chat completions should be inferred to be the requested service.

The intended logical sequence is ontology → KG → physical results → semantic policy → PPR → language explanation. Production paid model calls are deferred by the user; public-demo evidence remains a separate category. No local model deployment or weight download is required.

## Decision

1. `CityPack` is an immutable authoritative snapshot. A SQLite workspace stores validated typed Actions and scenario overlays. Replaying committed Actions must produce the same scenario hash.
2. Routing and SUMO own physical facts. Graph projection/PPR consumes those facts and permitted semantic policy. Policy cannot change permissions, speed, OD, capacity, travel time or a fire perimeter. Language explanations read frozen facts and provenance.
3. Baseline/event runs share network, demand, seeds and configuration except declared restrictions. A claimed delta-PPR uses the same node universe, seeds, alpha and policy. Policy-change experiments are separately labelled.
4. The product exposes a local HTTP API and embeddable Web Component/MapAdapter. The core remains independent of browser/server frameworks. Multi-user identity and municipal infrastructure remain deployer responsibilities.
5. Real SUMO uses pinned local executables, command arrays, bounded execution, permission-based hard closures, one combined concurrent rerouter and immutable evidence outputs. Required simulation checks never pass through a fake engine.
6. The System-One adapter follows SimpleJev's verified remote classifier contract. Only approved abstract relation definitions and objectives may leave the environment within explicit authorization. The current target model and endpoint distinction are recorded in the [runbook](../CURRENT_RUNBOOK.md).
7. Production SimpleJev, its public demo, optional ordinary `qwen_api`, cached replay, rules and test doubles have distinct provenance. Ordinary generated relevance cannot satisfy the classifier gate. Classifier outputs themselves are not assumed calibrated to real-world correctness.
8. Production paid checks remain `DEFERRED_USER`, with budget/egress disabled. Public-demo checks retain separate scope and accounting. Account links are informational only; do not require an ordinary Qwen key or reopen production spending until the user resumes it.

## Consequences

Deterministic ontology, KG, PPR, routing and native SUMO work continues independently. Remote model uncertainty does not justify changing physical facts or marking an unperformed integration successful. Model usefulness requires separate independent evaluation; protocol success alone cannot establish improvement.

The source plan's mandatory local GPU/model deployment is superseded. Its truthful provenance, typed-output discipline and independent validation remain applicable, but the current protocol must match SimpleJev rather than an assumed Reflex or chat-completions protocol.

Measured traffic prediction remains a separate claim requiring independent observations. This ADR does not authorize spending, data upload, publication or new product scope. Alternatives outside v1 include QGIS-only delivery, author-operated SaaS, fire-physics/3D engines, a generic plugin marketplace and public-resource allocation recommendations.
