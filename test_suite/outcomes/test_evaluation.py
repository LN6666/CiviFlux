import ast
import json
from pathlib import Path

from experiments.dataset import freeze, make_case
from experiments.evaluation import recall_at
from experiments.oracle import labels

ROOT = Path(__file__).resolve().parents[2]


def test_oracle_is_independent_and_known_answers():
    source = (ROOT / "experiments/oracle.py").read_text()
    imports = [n.module for n in ast.walk(ast.parse(source)) if isinstance(n, ast.ImportFrom)]
    assert not any(m and (m.startswith("urbanimpact") or m.startswith("adapters")) for m in imports)
    dual = make_case("dual_corridor", 0)
    answer = labels(dual["city"], dual["scenario"])
    hospital = next(r for r in answer["od"] if r["facility_id"] == "hospital")
    assert hospital["baseline"]["travel_time_s"] == 30
    assert hospital["event"]["travel_time_s"] == 70
    bridge = make_case("single_bridge", 0)
    expected = labels(bridge["city"], bridge["scenario"])
    assert (
        next(r for r in expected["od"] if r["facility_id"] == "hospital")["event"]["status"] == "unreachable"
    )
    missing = make_case("missing_data", 0)
    assert "hospital" in labels(missing["city"], missing["scenario"])["unknown_facility_ids"]


def test_group_frozen_split_and_model_label_separation(tmp_path):
    first = freeze(tmp_path)
    second = freeze(tmp_path)
    assert first == second and first["case_count"] == 48 and first["motif_count"] == 12
    sets = [set(v) for v in first["splits"].values()]
    assert not (sets[0] & sets[1] or sets[1] & sets[2] or sets[0] & sets[2])
    cases = json.loads((tmp_path / "experiments/frozen/cases.json").read_text())
    assert len({c["case_id"] for c in cases}) == 48
    assert all("labels" not in c and "affected_facility_ids" not in c["city"] for c in cases)
    assert first["model_inputs_allowlist"] == ["objective", "relation semantic definitions"]


def test_empty_and_short_retrieval_metrics():
    empty = recall_at([], set(), 10)
    assert empty["recall"] is None and empty["precision"] is None
    score = recall_at(["a", "b"], {"a", "c"}, 10)
    assert score["k_requested"] == 10 and score["k_returned"] == 2 and score["candidate_count"] == 2
    assert score["recall"] == score["precision"] == 0.5


def test_actual_ablation_has_shared_facts_zero_violations_and_deferred_models():
    path = ROOT / "evidence/wp6/raw_metrics.json"
    assert path.exists(), "run scripts/evaluate.py ablate before outcome gate"
    rows = json.loads(path.read_text())
    assert len(rows) == 48 * 6
    for caseid in {r["case_id"] for r in rows}:
        group = [r for r in rows if r["case_id"] == caseid]
        assert len({r["physical_hash"] for r in group}) == 1
        actual = [r for r in group if r["status"] == "PASS"]
        assert {r["variant"] for r in actual} == {"A0", "A1", "A2", "A5"}
        assert len({r["physical_cache_key"] for r in actual}) == 1
        assert all(
            r["oracle"]["constraint_violations"] == 0
            and r["oracle"]["mandatory_facility_check_coverage"] == 1
            and r["oracle"]["max_travel_time_error_s"] < 1e-9
            for r in actual
        )
        ppr = [r for r in actual if r["variant"] in {"A2", "A5"}]
        assert ppr[0]["ranking"] == ppr[1]["ranking"]
        if actual[0]["group"] in {"zero_disturbance", "time_boundary", "vehicle_class"}:
            assert all(r["no_op_max_abs_delta"] == 0 for r in ppr)
        assert all(r["status"] == "DEFERRED_USER" for r in group if r["variant"] in {"A3", "A4"})


def test_ontology_mutations_replay_and_benchmark_actual_evidence():
    checks = json.loads((ROOT / "evidence/wp6/ontology_ablation.json").read_text())
    assert len(checks) == 48
    assert all(
        c["typed_validator_rejected_mutation"]
        and c["scenario_replay_success"]
        and c["authoritative_snapshot_unchanged"]
        and c["evidence_trace_completeness"] == 1
        for c in checks
    )
    benchmark = json.loads((ROOT / "evidence/wp6/benchmark.json").read_text())
    assert benchmark["edges"] == benchmark["csr_nnz"] == 200000
    assert benchmark["status"] == "PASS" and benchmark["deterministic_repeated_run"]
    assert benchmark["residual_l1"] < 1e-12 and benchmark["provider_calls"] == 0


def test_comparison_cells_and_real_external_smoke_are_scoped():
    import csv

    rows = list(csv.DictReader((ROOT / "comparison/feature_matrix.csv").open()))
    assert len(rows) == 152
    assert all(
        r["status"] in {"yes", "no", "partial", "unknown"}
        and r["source"]
        and r["checked_on"]
        and r["verification_basis"]
        for r in rows
    )
    assert any(r["status"] == "unknown" for r in rows)
    evidence = json.loads((ROOT / "evidence/wp6/external_reproduction.json").read_text())
    assert evidence["commit"] == "f06f6098626eb184bb3a3334b1b20639dda6b842"
    assert evidence["exit_code"] == 0 and evidence["http"]["status_code"] == 200
    assert evidence["simulation_results"][0]["Vehicles Inserted"] > 0
    assert evidence["remote_connections_attempted"] == evidence["llm_calls"] == 0
    assert evidence["source_modified"] is False
    assert "ignore-route-errors" in evidence["limitations"][0]
