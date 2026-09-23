# Ontology / KG / PPR independent review

Date: 2026-09-24. Scope: typed registry/contracts, action transaction/replay, ontology read model, projection construction, paired PPR validation and run-bound Object View. Production fixes were made by the integrator, except the authorized ontology read-model and Object View corrections. The original reproducer assertions remain; no xfail, skip or relaxed threshold was introduced.

## Result

All **23 independent ontology/graph regression cases** now pass. This is a count of test cases, not 23 distinct bugs: typed-link direction, transactional rollback, replay after rejection and finite solver parameters also preserve invariants that already passed when checked. Two additional Object View regression cases pass. No concrete severe finding remains unresolved within this reviewed scope.

The combined affected suite completed with exit code 0: **56 passed, 1 warning in 11.01s**. The warning is upstream Starlette's deprecation of the current httpx TestClient integration; it is not a skipped check.

```bash
PYTHONPATH=core:. uv run --frozen python -m pytest -q \
  test_suite/unit/test_network.py test_suite/unit/test_graph_ranking.py \
  test_suite/review test_suite/sumo test_suite/integration/test_api.py --tb=short
```

Safe import cleanup (`ruff check --select I,F401 --fix`) and formatting were completed before this run for the owned network, ontology, SUMO, review tests, demo script and API service files. The SUMO tests invoke the actual pinned local executables.

## Findings and disposition

| Finding / invariant | Concrete failure or risk | Disposition |
|---|---|---|
| Authoritative identity/provenance | Unregistered source IDs, duplicate source IDs with conflicting hashes and cross-type object IDs were accepted | CityPack validation now rejects all three |
| Registered projection | Unknown profile/version could claim accepted semantics | Project validates registered profile and ontology version |
| Paired context and policy | Different snapshot/time/objective/policy/projection kind, or scores not bound to policy hash, could be compared | Paired validation requires matching context and rehashes the applied policy |
| Projection integrity | Corrupt payload/universe hashes were accepted; a self-consistently rehashed graph could still admit audit objects or reversed typed endpoints | Hashes and typed projection allowlist are independently reconstructed and validated |
| Road permissions | Operational graph could retain a turn through a road forbidden to the analyzed vehicle class | Road and turn class permissions are intersected |
| Witness memory bound | Layered DAG queued more than 10,000 copied paths before reaching the visited budget | Enqueue and visited counts share the bounded search budget |
| Typed links / Actions | Reversed facility links, record-construction failure and rejected actions must not mutate accepted state | Original direction, rollback and replay checks pass unchanged |
| Ontology run binding | Run facts could be materialized against a later overlay or another snapshot | Materialization requires exact city/scenario IDs and snapshot/overlay hashes |
| Assumed fire evidence | Assumed restrictions became verified incident links with no effective interval | Links preserve assumed confidence, restriction identity and `[start,end)` validity |
| Selected-run Object View | View loaded current workspace scenario/history, mixing later edits with old facts or rejecting otherwise valid old runs | Loads immutable run scenario/actions, verifies history hash, rejects explicit scope mismatch; run ID alone resolves saved scenario |
| Static transit dependency | Static verified alignment disappeared from Object View after removal from operational ranking | Separate dependency-evidence links remain visible with explicit projection kind/stage; a restricted road has no operational path assertion |

Reproducers: [ontology/graph cases](../../test_suite/review/test_ontology_graph_review.py), [Object View cases](../../test_suite/review/test_object_view_review.py). The algorithm choice and primary-source comparisons are in [ADR 0002](../../docs/adr/0002-pagerank.md).

## Limits

These checks establish bounded engineering invariants, not citywide transport validity or model usefulness. Native SUMO uses declared synthetic demand. Helsinki source-to-road mappings still require independent human review; selected-origin facility checks do not establish all-origin accessibility. Production SimpleJev paid calls remain `DEFERRED_USER`; public-demo and protocol evidence must remain separate. Release acceptance still follows required gates and `execution/STATE.md`.
