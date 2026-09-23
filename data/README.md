# Helsinki reference citypack

`data/citypacks/helsinki-current/citypack.json` is a bounded motor-drivable case belt imported from the official HSL OSM extract with osmium and SUMO netconvert. It contains stable directed edge IDs, explicit turn connections, candidate facility access points, current GTFS coverage and candidate bus-shape associations. Detailed schedule tables remain in the adjacent hashed sidecar. Raw source bytes and large generated data stay local and are gitignored.

Reproduce after `make bootstrap`:

```sh
.venv/bin/python scripts/data_pipeline.py fetch --allow-egress
.venv/bin/python scripts/data_pipeline.py build
.venv/bin/python scripts/data_pipeline.py review
PYTHONPATH=core:. .venv/bin/python -m pytest -q test_suite/data
```

Fetching requires explicit egress; sources are fixed registered official URLs with time/byte/type limits. Cached bytes are checked against SHA256 and never silently replaced. The September 2026 sources cannot establish May 2026 historical conditions. The wider preliminary drivable network is retained locally under `helsinki-outer` for future boundary sensitivity analysis; its historical validity is also unverified.

OSM: © OpenStreetMap contributors, ODbL 1.0, distributed via HSL. GTFS: © HSL 2026, CC BY 4.0. See [HSL open-data terms](https://www.hsl.fi/en/hsl/open-data) and [OSM attribution](https://www.openstreetmap.org/copyright).

The source-informed road case and street-level fire case are explicit current-network what-if examples. Exact motor-road closure hours, exemptions, actual fire perimeter, independently reviewed facility entrances and measured event traffic outcomes remain unknown. The review map and CSV live in `evidence/wp1`; machine checks do not imply independent human approval. Netconvert's diagnostics remain available, including unsupported lane/conditional-restriction semantics. No actual cordon or safety radius is inferred.
