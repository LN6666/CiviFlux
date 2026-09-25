# Local city data and event CityPacks

`data/citypacks/helsinki-current/citypack.json` is a bounded motor-drivable case belt imported from the official HSL OSM extract with osmium and SUMO netconvert. It contains namespaced directed edge IDs within this frozen crop, explicit turn connections, candidate facility access points, current GTFS coverage and candidate bus-shape associations. Edge IDs alone are not a cross-crop geometry or travel-time guarantee. Detailed schedule tables remain in the adjacent hashed sidecar. Raw source bytes and large generated data stay local and are gitignored.

Reproduce after `make bootstrap`:

```sh
.venv/bin/python scripts/data_pipeline.py fetch --allow-egress
.venv/bin/python scripts/data_pipeline.py build
.venv/bin/python scripts/data_pipeline.py review
PYTHONPATH=core:. .venv/bin/python -m pytest -q test_suite/data
```

Fetching requires explicit egress; sources are fixed registered official URLs with time/byte/type limits. Cached bytes are checked against SHA256 and never silently replaced. The September 2026 sources cannot establish May 2026 historical conditions.

An enlarged road-network sensitivity check can be reproduced **without another download** from those frozen bytes:

```sh
PYTHONPATH=core:. uv run --frozen python scripts/boundary_sensitivity.py
```

It builds an ignored `helsinki-boundary-outer` citypack and writes the tracked [`helsinki_boundary_sensitivity.json`](../evidence/wp2/helsinki_boundary_sensitivity.json). With 48 shared candidate origin–facility pairs in each road and fire case, the inner and outer crops differed on 3 and 8 stage-specific results respectively; 3 inner candidate entrances could not be paired and are explicitly excluded. The independently converted larger crop also changes some shared edge geometry/travel weights and turn topology, which the report counts. This is a **negative boundary-stability finding**, not a corrected citywide estimate. The earlier local `helsinki-outer` preliminary artifact is not release evidence; use the reproducible script and its report.

OSM: © OpenStreetMap contributors, ODbL 1.0, distributed via HSL. GTFS: © HSL 2026, CC BY 4.0. See [HSL open-data terms](https://www.hsl.fi/en/hsl/open-data) and [OSM attribution](https://www.openstreetmap.org/copyright).

The source-informed road case and street-level fire case are explicit current-network what-if examples. Exact motor-road closure hours, exemptions, actual fire perimeter, independently reviewed facility entrances and measured event traffic outcomes remain unknown. The review map and CSV live in `evidence/wp1`; machine checks do not imply independent human approval. Netconvert's diagnostics remain available, including unsupported lane/conditional-restriction semantics. No actual cordon or safety radius is inferred.

## Berlin 2026 marathon and Baku 2026 F1 city graphs

The event builder imports **dated, pinned Geofabrik OSM PBF bytes** into a bounded motor-road CityPack. A separate `--multimodal` variant can add walking and cycling linear ways without changing the frozen motor-only pack. Both export ontology-typed `RoadSegment` objects and directed, vehicle-scoped graph links as deterministic gzip JSONL (`kg_objects.jsonl.gz`, `kg_links.jsonl.gz`). The multimodal variant is an OSM/SUMO candidate topology; it does not infer an event's walking/cycling restrictions, sidewalk geometry or observed impact. Neither builder injects announcement facts as actual city state or uses Qwen. Raw PBF and generated CityPacks/KGs remain ignored; tracked source registrations and small audit/candidate records support rebuilding.

```sh
.venv/bin/python scripts/data_pipeline.py fetch --source berlin-osm --allow-egress
.venv/bin/python scripts/build_event_citypack.py berlin-marathon-2026
.venv/bin/python scripts/build_event_citypack.py berlin-marathon-2026 --multimodal
.venv/bin/python scripts/map_berlin_closures.py

.venv/bin/python scripts/data_pipeline.py fetch --source baku-osm --allow-egress
.venv/bin/python scripts/build_event_citypack.py baku-f1-2026
.venv/bin/python scripts/build_event_citypack.py baku-f1-2026 --multimodal
.venv/bin/python scripts/baku_indirect_map.py
.venv/bin/python scripts/baku_active_indirect_probe.py
```

The Berlin source registration points to the frozen 22 September extract; its local filename reflects the original 24 September retrieval, not the OSM content date. The Baku source points to the 18 September extract, before the 19 September announced closure onset. Each `.source.json` records byte hash, source time and licence; a mismatch refuses silent replacement. The build audit in `data/citypacks/<case>/build_audit.json` records source and CityPack hashes, feature counts, KG file hashes and unverified boundaries. Rebuilds may change derived hashes if the converter environment changes; preserve an original audit for a frozen experiment.

The [Berlin multimodal audit](../evidence/events/berlin-2026-multimodal-kg-audit.json) and [Baku multimodal audit](../evidence/events/baku-2026-multimodal-kg-audit.json) record local KG counts and exact derived hashes. The [Baku active-mode indirect probe](../evidence/events/baku-2026-active-indirect-probe.json) is a hypothetical corridor sensitivity with replayed typed Actions and fixed pedestrian/bicycle speeds. It never promotes the motor-road announcement into an observed walking/cycling restriction.

Berlin's tracked [`closure-candidates.json`](event_cases/berlin-marathon-2026-closure-candidates.json) is **unreviewed**, machine-proposed street-to-directed-edge mapping from one official notice. The [pre-onset conditional probe](../evidence/events/berlin-2026-incremental-pre-onset-probe.json) froze a few synthetic OD routes before a planned 26 September closure; it is not an observed traffic effect. Other already-announced closures, vehicle exceptions, historical GTFS, measured demand, independent actual operation and event-hour directional road observations are missing. Do not run the freeze script again over its immutable output. For Baku source/validation limits see the [F1 audit](../docs/BAKU_2026_F1_DATA_FEASIBILITY.md). Neither case is a release-grade V2/V3 validation set yet.
