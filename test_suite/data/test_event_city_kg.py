import gzip
import json

from urbanimpact.citypack.knowledge_graph import export_city_kg
from urbanimpact.contracts import CityPack, Link, OntologyObject
from urbanimpact.fixtures import toy_city
from urbanimpact.ontology import materialize


def test_city_kg_preserves_direction_vehicle_scope_and_candidate_access(tmp_path):
    data = toy_city().model_dump(mode="json")
    for edge in data["edges"]:
        if edge["id"] == "bc":
            edge["allowed_vehicle_classes"] = ["passenger"]
    city = CityPack.model_validate(data)
    objects, evidence_links = materialize(city)
    report = export_city_kg(city, objects, evidence_links, tmp_path)
    with gzip.open(tmp_path / "kg_objects.jsonl.gz", "rt") as stream:
        exported_objects = [OntologyObject.model_validate_json(line) for line in stream]
    with gzip.open(tmp_path / "kg_links.jsonl.gz", "rt") as stream:
        exported_links = [json.loads(line) for line in stream]
    assert report["objects"] == len(exported_objects)
    links = [(Link.model_validate(record["link"]), record["applicable_vehicle_classes"]) for record in exported_links]
    turn = next((link, classes) for link, classes in links if link.relation_type.value == "ROAD_CONNECTS_TO" and link.src == "ab" and link.dst == "bc")
    assert turn[1] == ["passenger"]
    assert turn[0].confidence_status == "candidate"
    assert not any(link.src == "bc" and link.dst == "ab" for link, _ in links)
    access = next(link for link, _ in links if link.relation_type.value == "FACILITY_ACCESSED_VIA")
    assert access.src == "hospital" and access.dst == "ch"
    assert access.confidence_status == "candidate"  # Derived snap, even when fixture entrance was verified.


def test_city_kg_export_is_byte_stable_and_does_not_mutate_authoritative_city(tmp_path):
    city = toy_city()
    original = city.model_dump_json()
    objects, evidence_links = materialize(city)
    first = export_city_kg(city, objects, evidence_links, tmp_path / "first")
    second = export_city_kg(city, objects, evidence_links, tmp_path / "second")
    assert first == second
    assert city.model_dump_json() == original
    for artifact in first["artifacts"]:
        assert (tmp_path / "first" / artifact["path"]).read_bytes() == (
            tmp_path / "second" / artifact["path"]
        ).read_bytes()
