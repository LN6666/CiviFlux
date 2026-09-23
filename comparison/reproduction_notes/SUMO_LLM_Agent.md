# SUMO_LLM_Agent reproduction

Repository: https://github.com/xuyimingxym/SUMO_LLM_Agent

Pinned commit: `f06f6098626eb184bb3a3334b1b20639dda6b842`, MIT. Checked 2026-09-24. The complete checkout is 1.6 MB according to repository metadata; source remains unmodified under ignored `experiments/vendor/`.

Executed: `.venv/bin/python scripts/evaluate.py external`

Result: **PASS_BOUNDED_EXTERNAL_SMOKE**, child exit code `0`. Full details and logs are in `evidence/wp6/external_reproduction.json` and `external_smoke.log`.

The harness imports the reviewed upstream Flask module and checks its index with Flask's in-process test client. It runs the project's own `sumo_simulation()` loop for 10 simulated seconds using its supplied network/config, with real SUMO/TraCI. The only runtime overrides are executable location, simulation duration and presentation sleep. No source patch, public listener, external map load, AI call or credential is used. Python remote socket connections are refused during the test.

The upstream main block binds 0.0.0.0; the harness does not invoke it. Upstream config enables `ignore-route-errors`, which is retained and disclosed. This smoke establishes a bounded executable neighbor component, not complete application correctness or paid-agent reproduction. Its network, demand and tasks differ from CiviFlux; there is no comparative speed or accuracy score.

Recreate dependencies from the reviewed registry packages in an isolated target: `uv pip install --python .venv/bin/python --target experiments/vendor/deps flask flask-socketio openai-agents`. Exact installed versions are recorded in reproduction evidence. The upstream module imports Agents SDK unconditionally; it is present solely to import the unmodified module.
