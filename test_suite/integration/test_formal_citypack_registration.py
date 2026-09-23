"""The selected Helsinki case ring must be reachable through the local API."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from urbanimpact.contracts import CityPack, Source
from urbanimpact.fixtures import toy_city

from api.app import create_app
from api.citypacks import FORMAL_OUTER_PATH, FORMAL_REPORT_PATH, load_local_citypacks


def fake_formal_pack(root: Path) -> tuple[Path, Path, str]:
    city = toy_city()
    source = Source(
        id="S03-OSM",
        url="https://example.invalid/frozen.osm",
        sha256="a" * 64,
        retrieved_at="2026-09-23T00:00:00Z",
        license="ODbL-1.0",
    )
    data = city.model_dump(mode="python")
    data.update(
        citypack_id="helsinki-boundary-outer-test",
        network_temporality="current_snapshot",
        sources=[*data["sources"], source.model_dump(mode="python")],
    )
    frozen = CityPack.model_validate(data)
    path = root / FORMAL_OUTER_PATH
    path.parent.mkdir(parents=True)
    raw = frozen.model_dump_json().encode()
    path.write_bytes(raw)
    report_path = root / FORMAL_REPORT_PATH
    report_path.parent.mkdir(parents=True)
    report_path.write_text(
        json.dumps(
            {
                "status": "PASS_SCOPED_CURRENT_NETWORK_CASE_REPLAY",
                "formal_case_boundary": "outer",
                "crop_paths": {"outer": FORMAL_OUTER_PATH.as_posix()},
                "crop_citypack_sha256": {"outer": hashlib.sha256(raw).hexdigest()},
                "source_sha256": source.sha256,
                "fixed_candidate_target_count": 1,
                "inner_original_candidate_facilities": 2,
                "excluded_candidate_targets": [{"facility_id": "excluded-test"}],
                "native_entrance_resnap_ids": {"outer": ["resnapped-test"]},
                "cases": {
                    kind: {"outer_vs_further": {"observed_fixed_od_metric_stability": True}}
                    for kind in ("road", "fire")
                },
            }
        )
    )
    return path, report_path, frozen.citypack_id


def test_formal_outer_pack_is_server_registered_and_visible_to_web(tmp_path):
    _, _, outer_id = fake_formal_pack(tmp_path)
    with TestClient(create_app(tmp_path / "workspace", data_root=tmp_path)) as client:
        client.headers["Authorization"] = "Bearer " + client.get("/api/v1/session").json()["token"]
        packs = client.get("/api/v1/citypacks").json()
        assert {pack["citypack_id"] for pack in packs} == {"TOY-DUAL-CORRIDOR", outer_id}
        listed = next(pack for pack in packs if pack["citypack_id"] == outer_id)
        assert any("Original candidate entrances excluded: 1" in warning for warning in listed["warnings"])
        assert any("New scenarios and citywide" in warning for warning in listed["warnings"])
        geometry = client.get(f"/api/v1/citypacks/{outer_id}")
        assert geometry.status_code == 200
        assert geometry.json()["geojson"]["features"]
        assert geometry.json()["warnings"] == listed["warnings"]
        template = client.get(f"/api/v1/citypacks/{outer_id}/scenario-template")
        assert template.status_code == 200
        scenario = template.json()
        assert scenario["citypack_id"] == outer_id
        created = client.post(
            "/api/v1/actions",
            json={
                "action_id": "create-formal-outer-test",
                "action_type": "CreateScenario",
                "scenario_id": scenario["scenario_id"],
                "parameters": {"scenario": scenario},
            },
        )
        assert created.status_code == 201, created.text
        submitted = client.post(
            "/api/v1/runs",
            json={"citypack_id": outer_id, "scenario_id": scenario["scenario_id"]},
        )
        assert submitted.status_code == 202, submitted.text
        run_id = submitted.json()["run_id"]
        client.app.state.service.futures[run_id].result(timeout=10)
        assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "completed"
        assert client.get(f"/api/v1/runs/{run_id}/results").json()["attention"]["convergence"]


@pytest.mark.parametrize("tamper", ["pack", "report_status", "report_path", "missing_report", "unstable_case", "coverage"])
def test_unverified_formal_pack_fails_closed(tmp_path, tamper):
    pack_path, report_path, _ = fake_formal_pack(tmp_path)
    if tamper == "pack":
        pack_path.write_bytes(pack_path.read_bytes() + b" ")
    elif tamper == "missing_report":
        report_path.unlink()
    else:
        report = json.loads(report_path.read_text())
        if tamper == "report_status":
            report["status"] = "NOT_VALIDATED"
        elif tamper == "report_path":
            report["crop_paths"]["outer"] = "../../untrusted.json"
        elif tamper == "coverage":
            report["excluded_candidate_targets"] = []
        else:
            report["cases"]["fire"]["outer_vs_further"]["observed_fixed_od_metric_stability"] = False
        report_path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="Formal Helsinki"):
        load_local_citypacks(tmp_path)


def test_toy_only_never_reads_the_optional_local_pack(tmp_path):
    pack_path, _, _ = fake_formal_pack(tmp_path)
    pack_path.write_text("invalid CityPack")
    cities, scopes = load_local_citypacks(tmp_path, toy_only=True)
    assert [city.citypack_id for city in cities] == ["TOY-DUAL-CORRIDOR"]
    assert scopes == {}
