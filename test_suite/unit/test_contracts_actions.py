import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator
from urbanimpact.contracts import ActionRequest, Scenario
from urbanimpact.fixtures import toy_city, toy_scenario
from urbanimpact.actions import Workspace, ActionError
from urbanimpact.util import digest
from ontology.codegen import outputs


def create(workspace, scenario=None):
    s = scenario or toy_scenario()
    return workspace.commit(
        ActionRequest(
            action_id="create",
            action_type="CreateScenario",
            scenario_id=s.scenario_id,
            parameters={"scenario": s.model_dump(mode="json")},
        )
    )


def test_codegen_and_schemas():
    for path, content in outputs().items():
        assert Path(path).read_text() == content
    schema = json.loads(Path("contracts/generated/Scenario.schema.json").read_text())
    Draft202012Validator(schema).validate(toy_scenario().model_dump(mode="json"))


def test_atomic_replay_and_baseline(tmp_path):
    w = Workspace(tmp_path / "w.db", toy_city())
    before = digest(w.city)
    create(w)
    request = ActionRequest(
        action_id="policy",
        action_type="ChangeAnalysisPolicy",
        scenario_id="toy-road",
        parameters={"ranking": "A1", "objective": "transit_association"},
    )
    committed = w.commit(request)
    assert w.commit(request) == committed
    replay = w.replay("toy-road", tmp_path / "replay.db")
    assert digest(replay.scenario("toy-road")) == digest(w.scenario("toy-road"))
    assert digest(w.city) == before
    assert replay.history("toy-road") == w.history("toy-road")


def test_rejected_action_no_partial_mutation(tmp_path):
    w = Workspace(tmp_path / "w.db", toy_city())
    create(w)
    before = digest(w.scenario("toy-road"))
    bad = toy_scenario().restrictions[0].model_dump(mode="json")
    bad["id"] = "bad"
    bad["edge_ids"] = ["absent"]
    with pytest.raises(ActionError):
        w.commit(
            ActionRequest(
                action_id="bad",
                action_type="AddRoadRestriction",
                scenario_id="toy-road",
                parameters={"restriction": bad},
            )
        )
    assert digest(w.scenario("toy-road")) == before
    assert w.history("toy-road")[-1]["record"]["status"] == "rejected"


def test_llm_confirmation_stale_hash_and_evidence_upgrade(tmp_path):
    w = Workspace(tmp_path / "w.db", toy_city())
    create(w)
    with pytest.raises(ActionError, match="confirmation"):
        w.commit(
            ActionRequest(
                action_id="llm",
                action_type="ChangeAnalysisPolicy",
                scenario_id="toy-road",
                parameters={"ranking": "A2", "objective": "facility_access"},
                origin="llm",
            )
        )
    with pytest.raises(ActionError, match="Stale"):
        w.commit(
            ActionRequest(
                action_id="stale",
                action_type="ValidateScenario",
                scenario_id="toy-road",
                parameters={},
                expected_overlay_hash="bad",
            )
        )
    bad = toy_scenario().restrictions[0].model_dump(mode="json")
    bad["id"] = "forged"
    bad["evidence_kind"] = "observed"
    with pytest.raises(ActionError, match="attest"):
        w.commit(
            ActionRequest(
                action_id="forged",
                action_type="AddRoadRestriction",
                scenario_id="toy-road",
                parameters={"restriction": bad},
            )
        )


def test_snapshot_defensive_copy(tmp_path):
    w = Workspace(tmp_path / "w.db", toy_city())
    copy = w.city
    copy.transit["forged"] = True
    assert "forged" not in w.city.transit
    with pytest.raises(Exception):
        w.city.edges[0].speed_kph = 999


def test_bad_time_unknown_fields_no_default_fire_radius():
    d = toy_scenario().model_dump(mode="json")
    d["window"]["end"] = d["window"]["start"]
    with pytest.raises(ValueError):
        Scenario.model_validate(d)
    d = toy_scenario(kind="fire").model_dump(mode="json")
    d["incident"]["severity"] = "large"
    with pytest.raises(ValueError):
        Scenario.model_validate(d)
    assert toy_scenario(kind="fire").incident.perimeter is None


def test_scenario_and_action_reject_unsupported_ontology_version():
    from urbanimpact.contracts import Scenario, ActionRequest
    from urbanimpact.fixtures import toy_scenario

    payload = toy_scenario().model_dump(mode="json")
    assert payload["ontology_version"] == "1.0.0"
    with pytest.raises(ValueError):
        Scenario.model_validate({**payload, "ontology_version": "2.0.0"})
    with pytest.raises(ValueError):
        ActionRequest.model_validate(
            {
                "ontology_version": "2.0.0",
                "action_id": "future",
                "action_type": "CreateScenario",
                "scenario_id": payload["scenario_id"],
                "parameters": {"scenario": payload},
            }
        )
