"""Reproducibility and provenance checks for the offline SimpleJev control."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from urbanimpact.fixtures import toy_city, toy_scenario
from urbanimpact.network import Router
from urbanimpact.util import digest

from scripts import offline_policy_permutation as control


def test_exact_permutation_control_replays_committed_evidence(monkeypatch):
    calls = 0
    original = Router.compare

    def counted_compare(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Router, "compare", counted_compare)
    report = control.run_control()
    expected = json.loads(control.DEFAULT_REPORT.read_text())
    assert report["fixed_inputs"] == expected["fixed_inputs"]
    assert report["source"] == expected["source"]
    assert report["graph"]["active_relation_types"] == expected["graph"]["active_relation_types"]
    assert report["observed_frozen_policy"]["baseline_l1_from_neutral"] == pytest.approx(
        expected["observed_frozen_policy"]["baseline_l1_from_neutral"], abs=1e-10
    )
    assert report["permutation_distribution"]["baseline_l1_from_neutral"]["median"] == pytest.approx(
        expected["permutation_distribution"]["baseline_l1_from_neutral"]["median"], abs=1e-10
    )
    assert calls == 1  # The physical calculation is shared by all 720 policies.
    assert report["fixed_inputs"]["city"] == digest(toy_city())
    assert report["fixed_inputs"]["scenario"] == digest(toy_scenario())
    assert report["design"]["permutation_count"] == 720
    assert report["graph"]["distinct_transition_hashes"]["baseline"] > 1
    assert report["graph"]["distinct_transition_hashes"]["event"] == 1
    assert report["observed_frozen_policy"]["event_l1_from_neutral"] == 0
    assert report["source"]["remote_calls"] == report["source"]["paid_calls"] == 0


@pytest.mark.parametrize(
    "mutate",
    [
        lambda document: document["provenance"].update(paid_call_this_run=True),
        lambda document: document["policy"].update(resolved_model="ordinary-qwen-chat"),
        lambda document: document["policy"]["scores"].pop("ROAD_CONNECTS_TO"),
        lambda document: document["policy"]["scores"].update(ROAD_CONNECTS_TO=float("nan")),
    ],
)
def test_control_rejects_nonfrozen_or_invalid_policy(tmp_path: Path, mutate):
    document = json.loads(control.FROZEN_POLICY.read_text())
    mutate(document)
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        control.frozen_scores(path)
