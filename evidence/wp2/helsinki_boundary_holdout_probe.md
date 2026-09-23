# Helsinki outer/further held-out origin probes

The [machine report](helsinki_boundary_holdout_probe.json) adds an independent **origin selection**, not an independent traffic dataset, to the earlier 48-target [boundary case](helsinki_formal_boundary_case.json). The script uses the already frozen OSM-derived inner, outer and further CityPacks. Before routing, it hashes shared passenger junction IDs and selects two from each quadrant of the original inner bounding box. It excludes both original case origins and all original candidate entrance nodes. All eight selected nodes and their coordinates are recorded in the JSON report; no origin was retained or discarded based on its route result.

For each of the Road and Fire what-if scenarios, the eight origins produce 384 OD pairs to the same 48 candidate entrance nodes. Each pair has baseline and event stages, so each case compares 768 stage results between outer and further crops. Both cases had **zero status or travel-time differences exceeding the existing 1 second threshold**, zero changed paths among comparable available routes, and a largest available travel-time difference of 0.868 seconds. The Road event had eight unreachable OD results in each crop; their travel-time and distance values remained `null`.

This strengthens the observed stability of the **selected outer/further current-network boundary** beyond the original two case origins. It does not prove citywide convergence, measured historical disruption, verified facility access or emergency response times. The same three original candidate entrances remain excluded and the two native-crop entrance resnaps remain unresolved. G205 therefore remains partial until those entrance decisions receive independent source or human review, or the narrower 48-target case is explicitly accepted.

Reproduce after preparing the hashed frozen CityPacks described in [`data/README.md`](../../data/README.md):

```sh
PYTHONPATH=core:. .venv/bin/python scripts/boundary_holdout_probe.py
PYTHONPATH=core:. .venv/bin/python -m pytest -q test_suite/data/test_boundary_holdout_probe.py
```

The JSON records source, CityPack, boundary report, formal case report, scenario and script SHA-256 values. Its current SHA-256 is `835e86ebbb014f23884735342854ff9577ffeb5a10e1f6e2f803000451ab3bd6`.
