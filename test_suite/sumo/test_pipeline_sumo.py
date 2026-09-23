"""Actual simulator evidence survives physical-cache reuse and user export."""

import json
import zipfile

import pytest

from api.services import RunService
from urbanimpact.contracts import ActionRequest
from urbanimpact.fixtures import toy_city, toy_scenario
from urbanimpact.util import file_hash


@pytest.mark.sumo
def test_cached_simulation_exports_hash_bound_native_artifacts(tmp_path):
    city = toy_city()
    service = RunService(tmp_path, [city])
    try:
        results = []
        for index in range(2):
            scenario = toy_scenario().model_copy(
                update={
                    "scenario_id": f"cache-{index}",
                    "engine": "routing_sumo",
                    "ranking": "A2" if index == 0 else "A0",
                }
            )
            service.action(
                ActionRequest(
                    action_id=f"create-{index}",
                    action_type="CreateScenario",
                    scenario_id=scenario.scenario_id,
                    parameters={"scenario": scenario.model_dump(mode="json")},
                )
            )
            job = service.submit(city.citypack_id, scenario.scenario_id)
            service.futures[job["run_id"]].result(timeout=30)
            assert service.state(job["run_id"])["status"] == "completed"
            result = service.result(job["run_id"])
            results.append(result)
            archive = service.export(job["run_id"])
            with zipfile.ZipFile(archive) as bundle:
                manifest = json.loads(bundle.read("export_manifest.json"))
                assert "sumo/event.tripinfo.xml" in manifest["files"]
                for name, expected in result["facts"]["simulation"]["artifacts"].items():
                    assert manifest["files"]["sumo/" + name] == expected
                    assert file_hash(tmp_path / "runs" / job["run_id"] / "sumo" / name) == expected
        assert not results[0]["facts"]["physical_cache"]["hit"]
        assert results[1]["facts"]["physical_cache"]["hit"]
        assert results[0]["facts"]["simulation"] == results[1]["facts"]["simulation"]
    finally:
        service.close()
