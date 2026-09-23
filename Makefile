SHELL := /bin/bash
export PYTHONPATH := $(CURDIR)/core:$(CURDIR)
PY := uv run --frozen python
PYTEST := uv run --frozen pytest
.PHONY: bootstrap contracts test-contracts test-unit test-ontology test-actions test-network test-scenarios test-graph test-ppr test-systemone-contract test-systemone-local systemone-preflight test-sumo test-cancel demo-toy demo-road-fire demo-ranking demo-sumo-pair citypack-fetch citypack-build case-review test-data build-web test-web test-browser test-object-view demo-local demo-offline test-reference test-api test-fast test-all
bootstrap:
	uv sync --frozen
	npm --prefix web ci
contracts:
	$(PY) -m ontology.codegen
test-contracts:
	$(PY) -m ontology.codegen --check
	$(PYTEST) -q test_suite/unit/test_contracts_actions.py
test-unit:
	$(PYTEST) -q test_suite/unit
test-ontology test-actions test-scenarios:
	$(PYTEST) -q test_suite/unit/test_contracts_actions.py test_suite/unit/test_graph_ranking.py
test-network:
	$(PYTEST) -q test_suite/unit/test_network.py
test-graph test-ppr:
	$(PYTEST) -q test_suite/unit/test_graph_ranking.py
test-systemone-contract:
	$(PYTEST) -q test_suite/unit/test_system_one.py
systemone-preflight:
	$(PY) scripts/systemone_preflight.py
test-systemone-local:
	@echo 'Local Qwen is prohibited by user decision. Use API preflight; live paid calls are deferred.'
	@exit 2
test-sumo test-cancel:
	$(PYTEST) -q test_suite/sumo
demo-toy:
	$(PY) scripts/demo_product.py
demo-road-fire:
	$(PY) scripts/demo_product.py --kind road --out evidence/wp2/road_product.json
	$(PY) scripts/demo_product.py --kind fire --out evidence/wp2/fire_product.json
demo-ranking:
	$(PY) scripts/demo_product.py --out evidence/wp3/ranking_integration.json
demo-sumo-pair:
	$(PY) scripts/demo_sumo.py
citypack-fetch:
	$(PY) scripts/data_pipeline.py fetch --allow-egress
citypack-build:
	$(PY) scripts/data_pipeline.py build
case-review:
	$(PY) scripts/data_pipeline.py review
test-data:
	$(PYTEST) -q test_suite/data
build-web:
	npm --prefix web run build
test-web test-browser test-object-view:
	npm --prefix web run test:browser
demo-local demo-offline: build-web
	$(PY) -m api --port 8765
test-reference:
	$(PYTEST) -q tests
test-api:
	$(PYTEST) -q test_suite/integration
test-fast: test-contracts
	$(PYTEST) -q test_suite/unit test_suite/integration test_suite/review tests
test-all: test-fast test-data test-outcomes test-sumo test-browser
test-outcomes:
	$(PYTEST) -q test_suite/outcomes
ablate:
	$(PY) scripts/evaluate.py ablate
benchmark:
	$(PY) scripts/evaluate.py benchmark
report:
	$(PY) scripts/evaluate.py report
compare-neighbors:
	$(PY) scripts/evaluate.py external
release-check:
	$(PY) scripts/check_release.py evidence/current_product_release.json

security-check:
	$(PY) scripts/check_repository.py
	npm --prefix web audit --audit-level=high
clean-checkout-test:
	$(PY) scripts/clean_checkout.py
