# Contributing to CiviFlux

CiviFlux changes should make an authorized Road & Fire GIS use case work end to end. Read `AGENTS.md`, `README.md`, the current runbook and the active work package before editing. Treat the numbered design documents as source requirements; the current System-One target is Featherless SimpleJev with the user-selected Qwen classifier, with no local model deployment. Ordinary generative Qwen is an optional comparison, not a substitute. Production paid calls are DEFERRED_USER; public-demo checks have separate authorization/evidence.

## Development environment

```bash
uv sync --frozen
export PYTHONPATH="$PWD/core:$PWD"
uv run --frozen python -m pytest -q test_suite/unit
```

Web dependencies use `npm ci` in `web/`. Use the repository lockfiles; do not independently replace dependency versions to hide a failing check. Native SUMO execution requires version 1.27.1. Model, browser, native simulation and network acquisition checks must retain separate statuses.

## Ownership and contracts

Keep domain calculations in `core/urbanimpact/`, integration logic in `adapters/`, HTTP concerns in `api/`, and UI behavior in `web/`. The integrator owns shared Pydantic/TypeScript contracts, ontology manifests and lockfiles during parallel work. Give each worker disjoint files and one bounded deliverable. Do not overwrite another worker's edits.

Authoritative `CityPack` snapshots are immutable. Write scenario changes through typed Actions; validate before commit and preserve an `ActionRecord` and replayable hashes. Never mutate authoritative graph edges from a UI callback or LLM response. Ranking operates on a declared projection, not arbitrary audit records.

## Evidence and tests

Choose focused checks for the changed behavior, then run required gates at a work-package boundary. Maintain original independent reference checks in `tests/` and `verification/`; product implementation and tests belong elsewhere. Do not remove assertions, convert required live tests to skips, alter expected outcomes to match the implementation, or weaken acceptance thresholds to obtain positive ablations.

A completed work package records:

- exact command and exit code;
- scope and input mode (`synthetic`, current snapshot, historical, API, replay or test double);
- output and input hashes, relevant binary/model configuration, and evidence paths;
- passed, failed, skipped and blocked checks separately;
- remaining release blockers.

When a calculation is unchanged, reuse existing evidence. A scientific or physical change requires affected validation to run again. Keep physical inputs, demand, seeds and baseline/event normalization fixed across comparable variants. A negative Qwen ablation result is valid; fabricating improvement is not.

## Boundaries

Only explicit, bounded and authorized API calls may leave the environment. Keep keys in a gitignored local `.env`; never print keys, include them in command arguments, commit them or put them in a browser bundle. Any subsequently authorized model provider receives approved abstract relation definitions and objective identifiers, not city objects, notes, identities or coordinates. A key by itself is not a spending authorization.

Data downloads require explicit egress. Current datasets cannot be relabelled as historical. Fire perimeters and road permissions come from confirmed/imported evidence or clearly declared assumptions. No automatic emergency exceptions, dispatch advice, evacuation safety claims or public-resource allocation ranking.

Do not push, publish releases, deploy public services, contact third parties, install unreviewed remote scripts, or modify system security without authorization.

## Delivering a change

Describe the concrete behavior before and after, the tests that establish it, and the limits that remain. Update the current runbook when commands or deployment change; add an ADR only when an architectural decision changes. Keep `execution/STATE.md` short and point to detailed logs in `evidence/`. Stop after the requested outcome and required checks are satisfied.
