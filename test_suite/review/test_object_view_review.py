"""Run object views must preserve saved inputs and distinguish dependency evidence."""

import pytest
from urbanimpact.actions import ActionError
from urbanimpact.contracts import ActionRequest
from urbanimpact.fixtures import toy_city, toy_scenario

from api.services import RunService


@pytest.fixture
def completed_run(tmp_path):
    service = RunService(tmp_path, [toy_city()])
    scenario = toy_scenario()
    try:
        service.action(
            ActionRequest(
                action_id="create",
                action_type="CreateScenario",
                scenario_id=scenario.scenario_id,
                parameters={"scenario": scenario.model_dump(mode="json")},
            )
        )
        run = service.submit(scenario.citypack_id, scenario.scenario_id)
        service.futures[run["run_id"]].result(timeout=10)
        assert service.state(run["run_id"])["status"] == "completed"
        yield service, scenario, run["run_id"]
    finally:
        service.close()


def test_run_object_view_uses_saved_overlay_and_history_after_workspace_edit(completed_run):
    service, scenario, rid = completed_run
    original = service.object_view("bc", scenario.citypack_id, scenario.scenario_id, rid)
    service.action(
        ActionRequest(
            action_id="later-policy",
            action_type="ChangeAnalysisPolicy",
            scenario_id=scenario.scenario_id,
            parameters={"ranking": "A1", "objective": "transit_association"},
        )
    )
    assert service.workspace(scenario.citypack_id).scenario(scenario.scenario_id).ranking == "A1"
    assert service.object_view("bc", scenario.citypack_id, scenario.scenario_id, rid) == original
    assert service.object_view("bc", scenario.citypack_id, rid=rid) == original
    assert all(record["request"]["action_id"] != "later-policy" for record in original["history"])
    with pytest.raises(ActionError, match="Run scope mismatch"):
        service.object_view("bc", scenario.citypack_id, "another-scenario", rid)


def test_static_transit_dependency_stays_visible_but_separate_from_operational_links(completed_run):
    service, scenario, rid = completed_run
    view = service.object_view("bc", scenario.citypack_id, rid=rid)
    dependencies = [link for link in view["links"] if link.get("projection_kind") == "dependency_evidence"]
    assert {link["relation_type"] for link in dependencies} == {"ROUTE_USES_SEGMENT", "SEGMENT_USED_BY_ROUTE"}
    assert all(link["projection_stage"] == "dependency_evidence" for link in dependencies)
    assert all(link["derivation_id"] == "verified-transit-alignment" for link in dependencies)
    assert view["state"]["scenario"] == "restricted"
    assert not [link for link in view["links"] if link.get("projection_kind") == "operational"]
    operational = service.object_view("ad", scenario.citypack_id, rid=rid)
    assert any(link.get("projection_kind") == "operational" for link in operational["links"])
