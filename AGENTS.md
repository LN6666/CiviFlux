# Active override

Read execution/USER_DECISIONS.md first. User explicitly requires Qwen API access and prohibits local Qwen deployment. Imported local-Reflex-specific requirements below are historical and superseded for the active implementation. Never download weights or start local inference.

# UrbanImpact Road & Fire — repository rules

## Mission and hard boundary
Deliver GIS v1 as an embeddable WEB plugin and a data-local analysis core. Real road restrictions + fire-induced EXTERNAL network impacts. Include typed temporal KG, deterministic PageRank/PPR, real local Qwen System-One integration, routing, a working SUMO adapter, tests, ablations, an evidence-labelled Helsinki example. Do not replace this with a QGIS plugin, 3D viewer, SaaS, CFD fire model, or mock demo.

## Read-once execution
Start with README.md, docs/00_PRODUCT.md, docs/10_EXECUTION.md and execution/work_packages.json. Thereafter load only the active work package's required files. Treat MASTER_PLAN.md as a reference, not recurring context. Follow prompts/00_MASTER.md; record the current checkpoint in execution/STATE.md.

## Engineering truth
- A tool exit code, test log, produced artifact hash, and declared scope establish completion, not prose.
- The supplied verification/ and tests/ are independent reference checks, NOT the product. Build the product under core/, api/, web/, adapters/, test_suite/.
- Mock Qwen System-One != real local Qwen System-One. Missing local model/runtime/GPU => BLOCKED_ENVIRONMENT, never PASS. Continue unblocked work. No fake fallback may satisfy the Qwen gate.
- The reference backend is pinned Reflex + Qwen3.5-4B, served locally. No closed Jev provider account/key is required. Pin exact Reflex commit, Qwen revision, device/dtype/permutations and calibration hash for release.
- Runtime city data stays in the deployer environment. Initial model-weight download may use Hugging Face, but production can use a pre-fetched local cache/mirror.
- Use the pinned Reflex/Qwen System-One contract in docs/05_QWEN_SYSTEM_ONE.md. Do not invent free-text outputs; Choice/Score/Noul stay typed and schema-validated.
- OSM/GTFS current snapshots are NOT historical truth. Incident location + assumed cordon is NOT actual fire perimeter. Announcement replay is NOT measured traffic validation.
- PPR is attention/relevance, not risk, causality, evacuation safety, or response-time prediction. Preserve physical metrics independently. Do not rank public policy choices or automate public resource-allocation decisions.
- Keep baseline/event node universe, seeds, alpha, relation policy and normalization equal for a claimed delta-PPR. Log separate policy-change experiments.
- Qwen System-One may adjust soft semantic relevance only, never road permissions, fire perimeters, speed, OD demand, capacity, travel time or safety rules.
- The operational ontology is normative: Objects + Links + Interfaces + Actions + Functions + Evidence. Users/LLMs must not directly mutate authoritative city objects or graph edges. Scenario changes go through typed Actions and immutable overlays.
- Authoritative city snapshots are immutable; Actions modify scenario workspace only. Every committed Action emits an ActionRecord and must be replayable to the same scenario hash.
- The PPR graph is a ProjectionSpec over the ontology, not the ontology itself. Audit/evidence/run objects do not enter ranking unless explicitly allowlisted.
- Palantir is an architectural inspiration only. Do not copy proprietary code/API or add a Foundry dependency.

## Scope and safety
No mandatory external AI. No author-operated backend. Municipal multi-user infra, auth/SSO, backups, HA are deployer-owned. Still implement safe local API binding/token, strict input paths, no arbitrary command execution, bounded jobs, credential redaction, explicit egress permission.
Fire UI is planning/research support, not operational dispatch or a substitute for emergency services. Unknown hazard boundaries must be user-confirmed/imported; never infer a certified radius from a severity adjective.
Keep future plugin seams small; no generic plugin marketplace/framework in v1. Cheap LLM is an optional provider interface only and cannot block v1 or overwrite numbers.

## Work cadence / anti-token-waste
Work in WP0–WP7 large end-to-end batches; each batch implements + tests + produces a demonstrable artifact. At most 3 hypothesis-changing repair iterations per failure signature. Two external access failures => record and route around, not repeated search. Do not repeatedly replan. Do not ask the user to re-confirm established scope.
Parallel agents only for disjoint file ownership and bounded deliverables; one integrator controls shared contracts/lockfiles. If no agent tools exist, execute serially; never simulate collaboration.
Do not contact third parties, publish/push/release, enable paid API, install unreviewed remote scripts or change system security without user permission. Providing a key alone does not grant unlimited budget.

## Verification / review
Preserve independent oracles and original failing tests. Never lower thresholds/remove assertions to pass. Changes to acceptance thresholds require a documented rationale unrelated to obtaining a positive ablation result.
Ablation variants share data, demand, seeds and physical outputs. No forced claim that Qwen System-One outperforms fixed PPR. If it does not, keep the verified integration and report the negative result.
Run focused tests after a change, full gates at work-package boundaries. Report passed/failed/skipped/blocked separately. A skipped release-required test blocks release.
