"""Explicitly synthetic reproducible demonstration, never a real-city data fallback."""

from datetime import datetime, timedelta, timezone

from urbanimpact.contracts import CityPack, Scenario


def dual_corridor() -> tuple[CityPack, Scenario]:
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    xy = {"S": (-100, 0), "A": (0, 0), "B": (100, 0), "C": (200, 0), "D": (100, 200), "H": (300, 0)}
    specs = [
        ("sa", "S", "A", 100),
        ("ab", "A", "B", 100),
        ("bc", "B", "C", 100),
        ("ad", "A", "D", 250),
        ("dc", "D", "C", 250),
        ("ch", "C", "H", 100),
    ]
    city = CityPack.model_validate(
        dict(
            citypack_id="sumo-dual",
            network_temporality="synthetic",
            transit_temporality="unavailable",
            sources=[
                dict(
                    id="synthetic",
                    url="synthetic:dual-corridor",
                    sha256="0" * 64,
                    retrieved_at=at.isoformat(),
                    license="CC0",
                )
            ],
            nodes=[dict(id=n, lon=24 + x / 55600, lat=60 + y / 111200) for n, (x, y) in xy.items()],
            edges=[
                dict(
                    id=e,
                    source=a,
                    target=b,
                    length_m=length,
                    speed_kph=36,
                    allowed_vehicle_classes=["passenger", "emergency"],
                    source_id="synthetic",
                    external_id=e,
                )
                for e, a, b, length in specs
            ],
            facilities=[
                dict(
                    id="hospital",
                    type="Hospital",
                    name="Synthetic hospital",
                    lon=24,
                    lat=60,
                    entrance_node_id="H",
                    access_status="verified",
                    source_id="synthetic",
                    external_id="H",
                )
            ],
        )
    )
    scenario = Scenario.model_validate(
        dict(
            scenario_id="synthetic-close-bc",
            citypack_id=city.citypack_id,
            kind="road",
            analysis_at=at,
            window=dict(start=at, end=at + timedelta(seconds=300)),
            seed_spec=dict(entity_ids=["S"]),
            restrictions=[
                dict(
                    id="r",
                    edge_ids=["bc"],
                    blocked_classes=["passenger"],
                    valid_from=at,
                    valid_to=at + timedelta(seconds=300),
                    evidence_kind="assumed",
                    evidence_refs=["synthetic"],
                )
            ],
            assumptions=[
                dict(
                    id="synthetic-demand",
                    description="Synthetic dual-corridor demonstration, not city observations",
                    affects=["geometry", "demand", "restriction"],
                )
            ],
        )
    )
    return city, scenario
