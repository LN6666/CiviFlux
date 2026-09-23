"""Register local reference CityPacks without an upload or network request.

The enlarged Helsinki pack is usable only when its bytes match the frozen,
scoped boundary-case evidence. This does not validate arbitrary new scenarios.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from urbanimpact.contracts import CityPack
from urbanimpact.fixtures import toy_city

INNER_PATH = Path("data/citypacks/helsinki-current/citypack.json")
FORMAL_OUTER_PATH = Path("data/citypacks/helsinki-boundary-outer/citypack.json")
FORMAL_REPORT_PATH = Path("evidence/wp2/helsinki_formal_boundary_case.json")
MAX_FORMAL_PACK_BYTES = 64 * 1024 * 1024
FORMAL_REPORT_STATUS = "PASS_SCOPED_CURRENT_NETWORK_CASE_REPLAY"


def _verified_formal_outer(root: Path) -> tuple[CityPack, str]:
    path = root / FORMAL_OUTER_PATH
    report_path = root / FORMAL_REPORT_PATH
    if not report_path.is_file():
        raise ValueError("Formal Helsinki outer CityPack exists without its boundary evidence")
    report = json.loads(report_path.read_text())
    if (
        report.get("status") != FORMAL_REPORT_STATUS
        or report.get("formal_case_boundary") != "outer"
        or report.get("crop_paths", {}).get("outer") != FORMAL_OUTER_PATH.as_posix()
    ):
        raise ValueError("Formal Helsinki outer boundary evidence is not applicable")
    cases = report.get("cases", {})
    if set(cases) != {"road", "fire"} or any(
        case.get("outer_vs_further", {}).get("observed_fixed_od_metric_stability") is not True
        for case in cases.values()
    ):
        raise ValueError("Formal Helsinki Road/Fire boundary comparisons are incomplete")
    target_count = report.get("fixed_candidate_target_count")
    if type(target_count) is not int or target_count <= 0:
        raise ValueError("Formal Helsinki boundary target count is invalid")
    expected_hash = report.get("crop_citypack_sha256", {}).get("outer")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise ValueError("Formal Helsinki outer CityPack hash is missing")
    if path.stat().st_size > MAX_FORMAL_PACK_BYTES:
        raise ValueError("Formal Helsinki outer CityPack exceeds the local size bound")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError("Formal Helsinki outer CityPack differs from frozen boundary evidence")
    city = CityPack.model_validate_json(raw)
    osm_source = next((source for source in city.sources if source.id == "S03-OSM"), None)
    if (
        city.network_temporality != "current_snapshot"
        or not city.citypack_id.startswith("helsinki-boundary-outer-")
        or osm_source is None
        or osm_source.sha256 != report.get("source_sha256")
    ):
        raise ValueError("Formal Helsinki outer CityPack identity or source differs from evidence")
    scope = (
        f"Outer boundary comparison covers only {target_count} frozen candidate entrances "
        "in the recorded Road/Fire cases; new scenarios and citywide or historical "
        "claims remain unvalidated."
    )
    return city, scope


def load_local_citypacks(root: Path, *, toy_only: bool = False) -> tuple[list[CityPack], dict[str, str]]:
    """Load fixed local paths; fail closed if a present formal pack is unverified."""
    cities = [toy_city()]
    if toy_only:
        return cities, {}
    inner = root / INNER_PATH
    if inner.is_file():
        cities.append(CityPack.model_validate_json(inner.read_bytes()))
    outer = root / FORMAL_OUTER_PATH
    if not outer.is_file():
        return cities, {}
    formal_city, scope = _verified_formal_outer(root)
    if formal_city.citypack_id in {city.citypack_id for city in cities}:
        raise ValueError("Duplicate formal Helsinki outer CityPack ID")
    cities.append(formal_city)
    return cities, {formal_city.citypack_id: scope}
