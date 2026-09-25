# Changelog

## Unreleased — GIS v1 implementation

The repository has progressed from a specification/reference-test pack to a product codebase. Release readiness remains gated by current evidence; this section does not declare every live integration complete.

- Added immutable typed city snapshots, scenario Actions, SQLite action history, replayable hashes and explicit projection contracts.
- Added directed turn-aware routing with half-open time windows, explicit vehicle permissions, unavailable/unreachable distinctions, full facility checks and network-crop comparison.
- Added real local SUMO paired runs with shared network/demand/seed, permission-based hard closures, single-rerouter combined intervals, subprocess cancellation, resource limits and complete demand denominators.
- Produced native SUMO synthetic detour evidence and a bounded Helsinki corridor example with synthetic demand on a current OSM snapshot.
- Added current Helsinki OSM/GTFS acquisition, source hashes, evidence-labelled case mapping and candidate facility/transit associations.
- Added typed graph projections, deterministic PPR, physical-fact reuse and model-provider seams.
- The user-designated System-One service is Featherless SimpleJev with its Qwen classifier, accessed remotely without local weights/deployment. Ordinary Alibaba International generative Qwen remains a separate optional comparison and cannot substitute for this classifier. Production paid calls are `DEFERRED_USER`; public-demo evidence is labelled separately.
- Added a browser component/API integration path and current developer documentation. Consult browser/API evidence before claiming their release gates pass.
- Rebuilt an enlarged Helsinki road crop from frozen OSM bytes and recorded a negative fixed-OD boundary-sensitivity result; current city examples retain their limited scope.
- Added a real SUMO cyclic-network multi-closure rerouter regression and browser lifecycle/cancellation E2E checks.
- Added a deterministic CycloneDX 1.6 SBOM, content-addressed license/NOTICE inventory, explicit unknowns, portable lock verification and per-host native-file generation in CI.
- Updated the 54-goal ledger and cross-account handoff for these bounded validations. Paid model and independent human/historical verification gates remain open.
- Exhaustively permuted six frozen SimpleJev relation scores (720 orderings) in an offline graph control; the result tests implementation sensitivity, not model quality.
- Compared three nested Helsinki crops, then replayed the scoped 48-target outer-ring Road/Fire cases through typed Action, routing, KG projection and fixed PPR. Missing and resnapped entrances remain unresolved.
- Added a source-tiered historical backtest protocol and a read-only evidence preflight. No event-matched observed traffic outcomes are available for numeric validation.
- Added pinned Berlin and pre-closure Baku OSM imports, bounded road-only CityPacks and provenance-bearing ontology KG exports; froze an unreviewed Berlin incremental routing probe before a planned closure and documented Baku 2026 F1 source/validation limits. Neither constitutes observed event-impact accuracy.
- Pinned container build inputs and added an offline Linux CI smoke. Three initial runs exposed missing SUMO native libraries; adding `libxrender1`, `libatomic1` and concise ELF linker diagnostics led to a passing Linux `core`/`container` run. The container report is scoped to a synthetic city and disabled model egress.
- After PR #1 was squash-merged, moved subsequent work to a fresh branch/PR path. PR branch pushes now run a single pull-request workflow to avoid duplicate failure notifications.
- Protected `main` now requires both passing `core` and `container` checks before ordinary PR merges.

## Source pack — 2026-09-23, handoff-3-operational-ontology

The source pack contained the master plan, operational ontology requirements, work packages, candidate evidence, independent verification code and reference tests. It did not contain a completed GIS product. Its original README is preserved in `docs/HANDOFF_README.md`; numbered design documents remain traceable sources.

### Verified integration checkpoint (2026-09-24)

- Added explicit ontology version pins on Scenario and Actions, recorded projection time window/scope, and rejected incompatible versions.
- Separated static transit dependency evidence from event-operational routing; rejected rehashed but invalid typed graph payloads.
- SimpleJev Qwen3.8-27B free hosted API: three requests total, zero paid calls; genuine policy applied to toy and Helsinki via recorded cache replay without changing physical facts. This is not calibration or production acceptance.
- Core/data/SUMO/outcome/reference Python checks:207passed; real browser workflows:6passed. Public release remains incomplete until independent data/model/deployment gates are met.
- Added a 54-goal acceptance ledger, current release evidence manifest, account-safe Codex handoff and traceability from user requirements to modules/tests. Published the public `LN6666/CiviFlux` repository; its first GitHub Actions run passed. This is a source handoff, not a full v1 release.
- Pinned GitHub Actions to verified current Node 24 action commits and the Ubuntu 24.04 runner after the first green CI reported upcoming platform migrations; retained the project Python 3.12/Node 22 versions.
- Protected `main` with the `core` CI check, code-owner review, linear history, and force-push/deletion prevention for future cross-account contributions.
