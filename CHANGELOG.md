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

## Source pack — 2026-09-23, handoff-3-operational-ontology

The source pack contained the master plan, operational ontology requirements, work packages, candidate evidence, independent verification code and reference tests. It did not contain a completed GIS product. Its original README is preserved in `docs/HANDOFF_README.md`; numbered design documents remain traceable sources.
