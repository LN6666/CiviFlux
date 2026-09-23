from __future__ import annotations

from urbanimpact.contracts import MANIFEST, Link, OntologyObject
from urbanimpact.util import digest


def validate_registry() -> None:
    for key in ("object_types", "link_types", "interfaces", "action_types", "functions", "projections"):
        names = [x["name"] for x in MANIFEST[key]]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate registry name: {key}")
    obj = {x["name"]: x for x in MANIFEST["object_types"]}
    interfaces = {x["name"] for x in MANIFEST["interfaces"]}
    for value in obj.values():
        if set(value["interfaces"]) - interfaces:
            raise ValueError("Unknown interface")
    for link in MANIFEST["link_types"]:
        if {link["src"], link["dst"]} - (set(obj) | interfaces):
            raise ValueError("Unknown link endpoint type")
    for p in MANIFEST["projections"]:
        if set(p["allowed_object_types"]) - set(obj):
            raise ValueError("Unknown projection object type")
        if set(p["allowed_link_types"]) - {x["name"] for x in MANIFEST["link_types"]}:
            raise ValueError("Unknown projection relation")


def implements(object_type: str, capability: str) -> bool:
    return object_type == capability or capability in next(
        x["interfaces"] for x in MANIFEST["object_types"] if x["name"] == object_type
    )


def validate_links(objects: list[OntologyObject], links: list[Link]) -> None:
    objects_by_id = {o.object_id: o for o in objects}
    if len(objects_by_id) != len(objects):
        raise ValueError("Duplicate ontology object")
    if len({x.id for x in links}) != len(links):
        raise ValueError("Duplicate link")
    for link in links:
        spec = next(x for x in MANIFEST["link_types"] if x["name"] == link.relation_type.value)
        for key, oid in [("src", link.src), ("dst", link.dst)]:
            if oid not in objects_by_id:
                raise ValueError("Orphan link endpoint")
            if not implements(objects_by_id[oid].object_type.value, spec[key]):
                raise ValueError("Incompatible link endpoint")


def registry_hash() -> str:
    validate_registry()
    return digest(MANIFEST)
