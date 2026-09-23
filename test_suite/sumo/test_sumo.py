import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from threading import Event, Timer

import pytest
from urbanimpact.contracts import CityPack, Scenario

from adapters.sumo import Demand, Limits, SimulationFailure, SumoAdapter
from adapters.sumo.adapter import _run_bounded

T = datetime(2026, 1, 1, tzinfo=timezone.utc)


def fixture(closure="bc", classes=("passenger",), begin=0, end=300):
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
                    id="synthetic", url="fixture", sha256="0" * 64, retrieved_at=T.isoformat(), license="CC0"
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
                    name="Fixture hospital",
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
            scenario_id="sumo-event",
            citypack_id=city.citypack_id,
            kind="road",
            analysis_at=T,
            window=dict(start=T, end=T + timedelta(seconds=300)),
            seed_spec=dict(entity_ids=["S"]),
            restrictions=[]
            if closure is None
            else [
                dict(
                    id="r",
                    edge_ids=list(closure) if isinstance(closure, tuple) else [closure],
                    blocked_classes=classes,
                    valid_from=T + timedelta(seconds=begin),
                    valid_to=T + timedelta(seconds=end),
                    evidence_kind="announced",
                    evidence_refs=["synthetic"],
                )
            ],
        )
    )
    return city, scenario


def run(tmp_path, closure="bc", demands=None, **kwargs):
    c, s = fixture(closure, **kwargs)
    return SumoAdapter().run_pair(
        c, s, demands or [Demand("v0", ("sa", "ab", "bc", "ch"))], tmp_path, Limits(duration_s=300)
    )


@pytest.mark.sumo
def test_real_detour_shared_demand_and_seed(tmp_path):
    report = run(tmp_path / "a")
    assert report["engine"] == "real_local_sumo"
    assert report["baseline"]["arrived"] == report["event"]["arrived"] == 1
    assert report["baseline"]["routes"]["v0"]["edges"] == ["sa", "ab", "bc", "ch"]
    assert report["event"]["routes"]["v0"]["edges"] == ["sa", "ad", "dc", "ch"]
    assert report["event"]["mean_arrived_duration_s"] > report["baseline"]["mean_arrived_duration_s"]
    repeat = run(tmp_path / "b")
    assert repeat["baseline"]["metrics_sha256"] == report["baseline"]["metrics_sha256"]
    assert report["baseline"]["teleported"] == report["event"]["teleported"] == 0
    assert all("--ignore-route-errors" not in c["command"] for c in report["commands"])


@pytest.mark.sumo
def test_unique_corridor_hard_closure_never_crossed_and_unfinished_denominator(tmp_path):
    report = run(tmp_path, "ch")
    event = report["event"]
    assert event["arrived"] == 0
    assert event["unfinished"] == event["demand_total"] == 1
    assert event["mean_arrived_duration_s"] is None
    assert event["teleported"] == 0
    assert event["routes"]["v0"]["arrival_s"] < 0
    times = event["routes"]["v0"]["exit_times_s"]
    assert len(times) < 4 or times[3] < 0
    closures = ET.parse(tmp_path / "event.add.xml").findall(".//closingReroute")
    assert all("allow" in e.attrib or "disallow" in e.attrib for e in closures)


@pytest.mark.sumo
def test_explicit_class_exception_and_simultaneous_closures(tmp_path):
    demands = [
        Demand("car", ("sa", "ab", "bc", "ch")),
        Demand("fire", ("sa", "ab", "bc", "ch"), "emergency", 5),
    ]
    report = run(tmp_path / "class", demands=demands)
    assert report["event"]["routes"]["car"]["edges"] == ["sa", "ad", "dc", "ch"]
    assert report["event"]["routes"]["fire"]["edges"] == ["sa", "ab", "bc", "ch"]
    both = run(tmp_path / "both", ("bc", "dc"))
    assert both["event"]["arrived"] == 0 and both["event"]["unfinished"] == 1
    assert len(ET.parse(tmp_path / "both" / "event.add.xml").findall("rerouter")) == 1
    assert len(both["event"]["routes"]["v0"]["edges"]) <= 4


@pytest.mark.sumo
def test_closure_end_reopens_real_road(tmp_path):
    report = run(tmp_path, end=30)
    later = run(
        tmp_path.parent / (tmp_path.name + "-after"),
        demands=[Demand("v0", ("sa", "ab", "bc", "ch"), depart_s=31)],
        end=30,
    )
    assert report["closure_intervals"][0]["end_s"] == 30
    assert later["event"]["routes"]["v0"]["edges"] == ["sa", "ab", "bc", "ch"]
    assert later["event"]["metrics_sha256"] == later["baseline"]["metrics_sha256"]


def test_invalid_route_is_failed_and_not_published(tmp_path):
    c, s = fixture()
    with pytest.raises(ValueError, match="Disconnected"):
        SumoAdapter().run_pair(c, s, [Demand("bad", ("sa", "ch"))], tmp_path)
    assert not (tmp_path / "sumo_pair.json").exists()
    assert (tmp_path / "failure.json").exists()


def test_cancel_kills_subprocess_tree(tmp_path):
    cancel = Event()
    script = "import subprocess,time,pathlib; p=subprocess.Popen(['sleep','60']); pathlib.Path('child.pid').write_text(str(p.pid)); time.sleep(60)"
    timer = Timer(0.5, cancel.set)
    timer.start()
    try:
        with pytest.raises(SimulationFailure) as caught:
            _run_bounded([sys.executable, "-c", script], tmp_path, "cancel", Limits(), cancel)
        assert caught.value.status == "CANCELLED"
        pid = int((tmp_path / "child.pid").read_text())
        # A reaped or zombie process is no longer executing; check via bounded ps.
        import subprocess

        status = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True
        ).stdout.strip()
        assert not status or status.startswith("Z")
    finally:
        timer.cancel()


def test_wallclock_output_limit_and_error_log_fail(tmp_path):
    with pytest.raises(SimulationFailure) as caught:
        _run_bounded(
            [sys.executable, "-c", "import time; time.sleep(20)"],
            tmp_path / "time",
            "slow",
            Limits(wallclock_s=0.1),
        )
    assert caught.value.status == "RESOURCE_LIMIT"
    with pytest.raises(SimulationFailure) as caught:
        _run_bounded(
            [sys.executable, "-c", 'print("x"*3000)'],
            tmp_path / "size",
            "large",
            Limits(max_output_bytes=1000),
        )
    assert caught.value.status == "RESOURCE_LIMIT"
    with pytest.raises(SimulationFailure, match="failed"):
        _run_bounded(
            [sys.executable, "-c", 'print("Error: invalid route")'], tmp_path / "error", "bad", Limits()
        )


@pytest.mark.sumo
def test_real_start_boundary_and_cancel_adapter(tmp_path):
    before = run(tmp_path / "before", begin=120, end=240)
    assert before["event"]["metrics_sha256"] == before["baseline"]["metrics_sha256"]
    at_start = run(
        tmp_path / "start", demands=[Demand("v0", ("sa", "ab", "bc", "ch"), depart_s=120)], begin=120, end=240
    )
    assert at_start["event"]["routes"]["v0"]["edges"] == ["sa", "ad", "dc", "ch"]
    c, s = fixture()
    cancel = Event()
    import threading
    import time

    folder = tmp_path / "cancel-real"

    def monitor():
        while not cancel.is_set():
            if (folder / "baseline.log").exists():
                cancel.set()
                return
            time.sleep(0.005)

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    try:
        with pytest.raises(SimulationFailure) as caught:
            SumoAdapter().run_pair(
                c,
                s,
                [Demand("v0", ("sa", "ab", "bc", "ch"))],
                folder,
                Limits(step_length_s=0.01),
                cancel_event=cancel,
            )
        assert caught.value.status == "CANCELLED"
        assert not (folder / "sumo_pair.json").exists()
        assert (folder / "failure.json").exists()
    finally:
        cancel.set()
        monitor_thread.join(timeout=1)


@pytest.mark.sumo
def test_imported_turn_allowlist_is_preserved(tmp_path):
    from urbanimpact.contracts import Connection

    c, s = fixture()
    turns = [("sa", "ab"), ("ab", "bc"), ("bc", "ch"), ("sa", "ad"), ("ad", "dc"), ("dc", "ch")]
    c = c.model_copy(
        update={
            "connections": tuple(
                Connection(from_edge=a, to_edge=b, allowed_vehicle_classes=("passenger", "emergency"))
                for a, b in turns
            )
        }
    )
    report = SumoAdapter().run_pair(c, s, [Demand("v0", ("sa", "ab", "bc", "ch"))], tmp_path)
    assert report["event"]["routes"]["v0"]["edges"] == ["sa", "ad", "dc", "ch"]
