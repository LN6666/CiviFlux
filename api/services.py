"""Local application services: bounded jobs, immutable inputs, durable manifests."""

from __future__ import annotations

import json
import sqlite3
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event, RLock

from urbanimpact.actions import ActionError, Workspace
from urbanimpact.contracts import ActionRequest, CityPack, Scenario
from urbanimpact.fixtures import toy_city, toy_scenario
from urbanimpact.pipeline import AnalysisCancelled, AnalysisService
from urbanimpact.util import atomic_json, canonical, digest, file_hash


class RunService:
    def __init__(
        self,
        root: Path,
        cities: list[CityPack] | None = None,
        policy_backend=None,
        citypack_scope_warnings: dict[str, str] | None = None,
    ):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.cities = {c.citypack_id: c for c in cities or [toy_city()]}
        self.citypack_scope_warnings = dict(citypack_scope_warnings or {})
        if set(self.citypack_scope_warnings) - set(self.cities):
            raise ValueError("CityPack scope warning references an unknown CityPack")
        self.workspaces = {
            id: Workspace(root / "workspaces" / (digest(id) + ".sqlite"), city)
            for id, city in self.cities.items()
        }
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="civiflux")
        self.analysis = AnalysisService(root / "cache", policy_backend)
        self.lock = RLock()
        self.cancel_events = {}
        self.futures = {}
        self.db_path = root / "jobs.sqlite"
        with self.db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, citypack_id TEXT NOT NULL, scenario_id TEXT NOT NULL, input_hash TEXT NOT NULL, idempotency TEXT UNIQUE NOT NULL, state TEXT NOT NULL)"
            )
            for rid, raw in db.execute("SELECT id,state FROM runs").fetchall():
                state = json.loads(raw)
                if state["status"] in ("queued", "running"):
                    state.update(
                        status="failed",
                        stage="interrupted",
                        error={
                            "code": "PROCESS_RESTART",
                            "message": "Local process stopped before run finished",
                            "retryable": True,
                        },
                    )
                    db.execute("UPDATE runs SET state=? WHERE id=?", (canonical(state).decode(), rid))

    def db(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def close(self):
        for event in self.cancel_events.values():
            event.set()
        self.executor.shutdown(wait=True, cancel_futures=True)

    def workspace(self, cid):
        if cid not in self.workspaces:
            raise ActionError("Unknown citypack")
        return self.workspaces[cid]

    def find_workspace(self, sid):
        found = []
        for w in self.workspaces.values():
            try:
                w.scenario(sid)
                found.append(w)
            except ActionError:
                continue
        if len(found) != 1:
            raise ActionError("Scenario ID unknown or ambiguous; choose unique IDs")
        return found[0]

    def action(self, request: ActionRequest, validate=False):
        if request.action_type.value == "CreateScenario":
            w = self.workspace(request.parameters.get("scenario", {}).get("citypack_id"))
        else:
            w = self.find_workspace(request.scenario_id)
        return w.validate(request) if validate else w.commit(request)

    def state(self, rid):
        with self.db() as db:
            row = db.execute("SELECT state FROM runs WHERE id=?", (rid,)).fetchone()
        if not row:
            raise KeyError("Unknown run")
        return json.loads(row[0])

    def _update(self, rid, **changes):
        with self.lock, self.db() as db:
            current = self.state(rid)
            current.update(changes)
            db.execute("UPDATE runs SET state=? WHERE id=?", (canonical(current).decode(), rid))
            atomic_json(self.root / "runs" / rid / "run.json", current)
        return current

    def submit(self, cid, sid, idempotency=None):
        w = self.workspace(cid)
        s = w.scenario(sid)
        city = w.city
        request_hash = digest({"scenario": s.model_dump(mode="json"), "city": w.snapshot_hash})
        key = idempotency or str(uuid.uuid4())
        with self.lock, self.db() as db:
            old = db.execute("SELECT id,input_hash FROM runs WHERE idempotency=?", (key,)).fetchone()
            if old:
                if old[1] != request_hash:
                    raise ActionError("Idempotency key reused for different input")
                return self.state(old[0])
            count = sum(
                json.loads(r[0])["status"] in ("queued", "running")
                for r in db.execute("SELECT state FROM runs")
            )
            if count >= 4:
                raise ActionError("Job queue limit reached")
            rid = "run-" + uuid.uuid4().hex
            # Subprocess effects happen after the validated action; failures persist in job state.
            w.commit(
                ActionRequest(
                    action_id="start-" + rid,
                    action_type="RunScenario",
                    scenario_id=sid,
                    parameters={"run_id": rid},
                )
            )
            history = w.history(sid)
            state = {
                "run_id": rid,
                "citypack_id": cid,
                "scenario_id": sid,
                "status": "queued",
                "stage": "queued",
                "error": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status_url": "/api/v1/runs/" + rid,
                "input_hash": request_hash,
            }
            db.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?)",
                (rid, cid, sid, request_hash, key, canonical(state).decode()),
            )
            event = Event()
            self.cancel_events[rid] = event
            folder = self.root / "runs" / rid
            atomic_json(folder / "actions.json", history)
            atomic_json(
                folder / "input.json",
                {"scenario": s.model_dump(mode="json"), "source_snapshot_hash": w.snapshot_hash},
            )
        self.futures[rid] = self.executor.submit(self._execute, rid, city, s, folder, history, event)
        return state

    def _execute(self, rid, city, s, folder, history, event):
        try:
            if event.is_set():
                raise AnalysisCancelled()
            self._update(rid, status="running", stage="validating")
            scope_warning = self.citypack_scope_warnings.get(city.citypack_id)
            self.analysis.run(
                city,
                s,
                rid,
                folder,
                overlay_hash=digest(s),
                action_log_hash=digest(history),
                extra_limitations=(scope_warning,) if scope_warning else (),
                stage=lambda name: self._update(rid, stage=name),
                cancel=event,
            )
            with self.lock:
                if event.is_set():
                    raise AnalysisCancelled()
                self._update(
                    rid,
                    status="completed",
                    stage="completed",
                    finished_at=datetime.now(timezone.utc).isoformat(),
                )
        except BaseException as error:
            cancelled = (
                event.is_set()
                or isinstance(error, AnalysisCancelled)
                or getattr(error, "status", None) == "CANCELLED"
            )
            code = (
                "CANCELLED"
                if cancelled
                else (
                    "BLOCKED_API_SETUP"
                    if "BLOCKED" in str(error) or type(error).__name__ == "BlockedEnvironment"
                    else "ANALYSIS_FAILED"
                )
            )
            # Never expose arbitrary backend errors, credential headers, absolute paths or response bodies.
            self._update(
                rid,
                status="cancelled" if cancelled else "failed",
                stage="cancelled" if cancelled else "failed",
                error={
                    "code": code,
                    "message": "Run cancelled"
                    if cancelled
                    else (
                        "Qwen API configuration or authorized budget unavailable"
                        if code == "BLOCKED_API_SETUP"
                        else "Analysis failed; inspect local diagnostics"
                    ),
                    "retryable": False,
                },
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
            atomic_json(folder / "diagnostic.json", {"exception_type": type(error).__name__, "code": code})

    def cancel(self, rid):
        with self.lock:
            state = self.state(rid)
            if state["status"] in ("completed", "failed", "cancelled"):
                return state
            self.cancel_events[rid].set()
            w = self.workspace(state["citypack_id"])
            w.commit(
                ActionRequest(
                    action_id="cancel-" + rid,
                    action_type="CancelRun",
                    scenario_id=state["scenario_id"],
                    parameters={"run_id": rid},
                )
            )
            return self._update(rid, stage="cancelling")

    def result(self, rid):
        if self.state(rid)["status"] != "completed":
            raise ActionError("Results unavailable until run completes")
        return json.loads((self.root / "runs" / rid / "result.json").read_text())

    def export(self, rid):
        state = self.state(rid)
        self.result(rid)
        folder = self.root / "runs" / rid
        self.workspace(state["citypack_id"]).commit(
            ActionRequest(
                action_id="export-" + rid,
                action_type="ExportResultBundle",
                scenario_id=state["scenario_id"],
                parameters={"run_id": rid},
            )
        )
        files = [
            folder / name
            for name in (
                "result.json",
                "scenario.json",
                "ontology.json",
                "actions.json",
                "run.json",
                "input.json",
                "model_provenance.json",
            )
            if (folder / name).is_file()
        ]
        result = self.result(rid)
        for name, expected in result["facts"].get("simulation", {}).get("artifacts", {}).items():
            if Path(name).name != name or name in (".", ".."):
                raise ActionError("Invalid simulation artifact name")
            path = folder / "sumo" / name
            if not path.is_file() or path.is_symlink() or file_hash(path) != expected:
                raise ActionError("Simulation artifact integrity failure")
            files.append(path)
        manifest = {
            "run_id": rid,
            "files": {p.relative_to(folder).as_posix(): file_hash(p) for p in files},
            "scope": "results, simulation artifacts and provenance; excludes credentials and raw source documents",
        }
        atomic_json(folder / "export_manifest.json", manifest)
        target = folder / "result-bundle.zip"
        temporary = folder / ".export-pending.zip"
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in files + [folder / "export_manifest.json"]:
                z.write(p, p.relative_to(folder).as_posix())
        temporary.replace(target)
        return target

    def template(self, cid):
        city = self.cities[cid]
        if city.network_temporality == "synthetic":
            return toy_scenario().model_dump(mode="json")
        edge = next((e for e in city.edges if "passenger" in e.allowed_vehicle_classes), city.edges[0])
        start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=2)
        return Scenario.model_validate(
            {
                "scenario_id": "scenario-" + uuid.uuid4().hex[:12],
                "citypack_id": cid,
                "kind": "road",
                "analysis_at": start.isoformat(),
                "window": {"start": start.isoformat(), "end": end.isoformat()},
                "restrictions": [
                    {
                        "id": "restriction-1",
                        "edge_ids": [edge.id],
                        "valid_from": start.isoformat(),
                        "valid_to": end.isoformat(),
                        "blocked_classes": ["passenger"],
                        "evidence_kind": "assumed",
                        "evidence_refs": ["USER-ASSUMPTION"],
                    }
                ],
                "assumptions": [
                    {
                        "id": "user-defined",
                        "description": "User-selected current-network what-if restrictions; not historical observed traffic.",
                        "affects": ["restrictions"],
                    }
                ],
                "seed_spec": {"entity_ids": [edge.id]},
            }
        ).model_dump(mode="json")

    def object_view(self, oid, cid, sid=None, rid=None):
        from urbanimpact.network import compile_restrictions
        from urbanimpact.ontology import materialize

        w = self.workspace(cid)
        result = self.result(rid) if rid else None
        if result and (result["citypack_id"] != cid or (sid and result["scenario_id"] != sid)):
            raise ActionError("Run scope mismatch")
        if result:
            folder = self.root / "runs" / rid
            scenario = Scenario.model_validate_json((folder / "scenario.json").read_text())
            history = json.loads((folder / "actions.json").read_text())
            if digest(history) != result["action_log_hash"]:
                raise ActionError("Run action history integrity failure")
        else:
            scenario = w.scenario(sid) if sid else None
            history = w.history(sid) if sid else []
        objects, ontology_links = materialize(self.cities[cid], scenario, result)
        objects = {o.object_id: o for o in objects}
        if oid not in objects:
            raise KeyError("Unknown object")
        active = (
            compile_restrictions(self.cities[cid], scenario, scenario.analysis_vehicle_class)
            if scenario
            else set()
        )
        graph_links = []
        if result:
            for projection_name in ("event", "dependency_evidence"):
                projection = result["graph"].get(projection_name)
                if projection:
                    graph_links.extend(
                        {
                            **edge,
                            "projection_kind": projection["spec"]["projection_kind"],
                            "projection_stage": projection_name,
                        }
                        for edge in projection["links"]
                        if oid in (edge["src"], edge["dst"])
                    )
        return {
            "identity": objects[oid].model_dump(mode="json"),
            "state": {
                "baseline": "imported immutable",
                "scenario": "restricted" if oid in active else "baseline",
                "analysis_at": scenario.analysis_at.isoformat() if scenario else None,
                "vehicle_class": scenario.analysis_vehicle_class if scenario else None,
            },
            "links": graph_links
            + [e.model_dump(mode="json") for e in ontology_links if oid in (e.src, e.dst)],
            "facts": [
                x
                for x in result["facts"].get("od", [])
                if x.get("facility_id") == oid
                or oid in x["baseline"]["edge_ids"]
                or oid in x["event"]["edge_ids"]
            ]
            if result
            else [],
            "attention": [x for x in result["attention"].get("records", []) if x["object_id"] == oid]
            if result
            else [],
            "evidence": [s.model_dump(mode="json") for s in self.cities[cid].sources],
            "actions": ["AddRoadRestriction", "AttachEvidence"]
            if objects[oid].object_type.value == "RoadSegment"
            else ["AttachEvidence"],
            "history": history,
        }
