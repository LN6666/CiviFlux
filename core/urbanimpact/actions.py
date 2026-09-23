"""Atomic scenario overlays; all writes validated inside a SQLite transaction."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import MANIFEST, ActionRecord, ActionRequest, CityPack, Incident, Restriction, Scenario
from .util import canonical, digest


class ActionError(ValueError):
    pass


class Workspace:
    def __init__(self, path: Path, city: CityPack):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._snapshot = canonical(city)
        self.snapshot_hash = digest(city)
        with self.connect() as db:
            db.executescript(
                "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS scenarios (id TEXT PRIMARY KEY, data TEXT NOT NULL, hash TEXT NOT NULL); CREATE TABLE IF NOT EXISTS actions (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, scenario_id TEXT NOT NULL, envelope TEXT NOT NULL);"
            )
            old = db.execute("SELECT value FROM metadata WHERE key='snapshot_hash'").fetchone()
            if old and old[0] != self.snapshot_hash:
                raise ActionError("Workspace belongs to another immutable snapshot")
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('snapshot_hash', ?)", (self.snapshot_hash,))

    @property
    def city(self):
        # A fresh validated value prevents mutable nested dictionaries changing authoritative state.
        return CityPack.model_validate_json(self._snapshot)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def scenario(self, sid: str) -> Scenario:
        with self.connect() as db:
            row = db.execute("SELECT data FROM scenarios WHERE id=?", (sid,)).fetchone()
        if not row:
            raise ActionError("Unknown scenario")
        return Scenario.model_validate_json(row[0])

    def validate_scenario(self, scenario: Scenario) -> dict:
        city = self.city
        if scenario.citypack_id != city.citypack_id:
            raise ActionError("Wrong citypack")
        edges = {e.id for e in city.edges}
        source_ids = {s.id for s in city.sources}
        for restriction in scenario.restrictions:
            if set(restriction.edge_ids) - edges:
                raise ActionError("Unknown directed restriction edge")
            if set(restriction.evidence_refs) - source_ids and restriction.evidence_kind != "assumed":
                raise ActionError("Observed/announced restrictions require registered evidence")
            if restriction.evidence_kind != "assumed":
                claims = city.evidence.get("restriction_claims", {})
                claim = claims.get(restriction.id)
                if not claim or digest(claim) != digest(restriction):
                    raise ActionError("Evidence does not attest this restriction; preserve assumed status")
        if scenario.incident and scenario.incident.geometry_status == "verified":
            if not set(scenario.incident.source_refs).issubset(source_ids):
                raise ActionError("Verified incident lacks source")
            claims = city.evidence.get("incident_claims", [])
            if digest(scenario.incident) not in {digest(x) for x in claims}:
                raise ActionError("Location not independently verified")
        valid_seeds = (
            edges | {f.id for f in city.facilities} | {str(x["id"]) for x in city.transit.get("routes", [])}
        )
        if set(scenario.seed_spec.entity_ids) - valid_seeds:
            raise ActionError("Seeds must name projected city objects")
        return {
            "valid": True,
            "source_snapshot_hash": self.snapshot_hash,
            "network_temporality": city.network_temporality,
            "warnings": list(city.warnings),
            "assumptions": [a.model_dump(mode="json") for a in scenario.assumptions],
        }

    def _candidate(self, request: ActionRequest, current: Scenario | None) -> Scenario:
        name = request.action_type.value
        p = request.parameters
        required = set(next(a["parameters"] for a in MANIFEST["action_types"] if a["name"] == name))
        if set(p) != required:
            raise ActionError("Action parameters must match registered signature")
        if request.origin == "llm" and not request.user_confirmed:
            raise ActionError("LLM drafts require user confirmation")
        if name == "CreateScenario":
            if current is not None:
                raise ActionError("Scenario already exists")
            scenario = Scenario.model_validate(p["scenario"])
            if scenario.scenario_id != request.scenario_id:
                raise ActionError("Scenario identity mismatch")
        else:
            if current is None:
                raise ActionError("Unknown scenario")
            data = current.model_dump(mode="json")
            if name == "AddRoadRestriction":
                r = Restriction.model_validate(p["restriction"])
                data["restrictions"].append(r.model_dump(mode="json"))
            elif name == "CreateFireIncident":
                if current.incident:
                    raise ActionError("Incident already exists")
                data["kind"] = "fire"
                data["incident"] = Incident.model_validate(p["incident"]).model_dump(mode="json")
            elif name == "AttachImportedPerimeter":
                if not current.incident:
                    raise ActionError("Incident required")
                if p["source_ref"] not in {s.id for s in self.city.sources}:
                    raise ActionError("Unregistered perimeter source")
                from shapely.geometry import shape

                geom = shape(p["perimeter"])
                if geom.geom_type not in ("Polygon", "MultiPolygon") or not geom.is_valid or geom.is_empty:
                    raise ActionError("Invalid perimeter")
                data["incident"]["perimeter"] = p["perimeter"]
                data["incident"]["perimeter_source"] = "imported"
                data["incident"]["source_refs"] = sorted(
                    set(data["incident"]["source_refs"] + [p["source_ref"]])
                )
            elif name == "AttachEvidence":
                if p["source_ref"] not in {s.id for s in self.city.sources}:
                    raise ActionError("Unknown source")
                # An evidence attachment does not upgrade an assumption to an observed fact.
            elif name == "ChangeAnalysisPolicy":
                data["ranking"] = p["ranking"]
                data["objective"] = p["objective"]
            elif name in ("RunScenario", "CancelRun", "ExportResultBundle"):
                if not isinstance(p["run_id"], str) or not p["run_id"] or len(p["run_id"]) > 160:
                    raise ActionError("Invalid run ID")
            elif name == "CompareRuns":
                if (
                    not isinstance(p["run_ids"], list)
                    or len(p["run_ids"]) != 2
                    or not all(isinstance(x, str) for x in p["run_ids"])
                ):
                    raise ActionError("Two run IDs required")
            elif name != "ValidateScenario":
                raise ActionError("Unsupported action")
            scenario = Scenario.model_validate(data)
        self.validate_scenario(scenario)
        return scenario

    def validate(self, request: ActionRequest) -> dict:
        try:
            current = self.scenario(request.scenario_id)
        except ActionError:
            current = None
        before = digest(current) if current else None
        if request.expected_overlay_hash is not None and request.expected_overlay_hash != before:
            raise ActionError("Stale overlay hash")
        candidate = self._candidate(request, current)
        return {
            "valid": True,
            "before_hash": before,
            "after_hash": digest(candidate),
            "source_snapshot_hash": self.snapshot_hash,
        }

    def commit(self, request: ActionRequest, *, timestamp: datetime | None = None) -> dict:
        error = None
        envelope = None
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT envelope FROM actions WHERE id=?", (request.action_id,)).fetchone()
            if prior:
                envelope = json.loads(prior[0])
                if envelope["request"] != request.model_dump(mode="json"):
                    raise ActionError("Action ID reused with different input")
                if envelope["record"]["status"] != "committed":
                    raise ActionError("Action was rejected")
                return envelope
            row = db.execute("SELECT data FROM scenarios WHERE id=?", (request.scenario_id,)).fetchone()
            current = Scenario.model_validate_json(row[0]) if row else None
            before = digest(current) if current else None
            try:
                if request.expected_overlay_hash is not None and request.expected_overlay_hash != before:
                    raise ActionError("Stale overlay hash")
                candidate = self._candidate(request, current)
                after = digest(candidate)
                db.execute(
                    "INSERT INTO scenarios VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data,hash=excluded.hash",
                    (request.scenario_id, canonical(candidate).decode(), after),
                )
            except (ValueError, KeyError, TypeError) as exc:
                error = ActionError(str(exc))
                after = before
            record = ActionRecord(
                action_id=request.action_id,
                action_type=request.action_type,
                timestamp=timestamp or datetime.now(timezone.utc),
                parameters_hash=digest(request.parameters),
                actor_context=request.actor_context,
                input_object_refs=(request.scenario_id,),
                precondition_results=({"name": "typed_validation", "passed": error is None},),
                output_object_refs=(request.scenario_id,) if error is None else (),
                status="committed" if error is None else "rejected",
                error={"code": "INVALID_ACTION", "message": str(error)} if error else None,
                provenance_hash=digest(
                    {
                        "request": request.model_dump(mode="json"),
                        "before": before,
                        "after": after,
                        "snapshot": self.snapshot_hash,
                    }
                ),
            )
            envelope = {
                "request": request.model_dump(mode="json"),
                "record": record.model_dump(mode="json"),
                "before_hash": before,
                "after_hash": after,
                "snapshot_hash": self.snapshot_hash,
            }
            db.execute(
                "INSERT INTO actions(id,scenario_id,envelope) VALUES (?,?,?)",
                (request.action_id, request.scenario_id, canonical(envelope).decode()),
            )
        if error:
            raise error
        return envelope

    def history(self, sid: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [
                json.loads(row[0])
                for row in db.execute("SELECT envelope FROM actions WHERE scenario_id=? ORDER BY seq", (sid,))
            ]

    def replay(self, sid: str, destination: Path) -> "Workspace":
        if destination.exists():
            raise ActionError("Replay destination must be empty")
        replay = Workspace(destination, self.city)
        for env in self.history(sid):
            if env["record"]["status"] != "committed":
                continue
            request = ActionRequest.model_validate(env["request"])
            try:
                before = digest(replay.scenario(sid))
            except ActionError:
                before = None
            if before != env["before_hash"]:
                raise ActionError("Replay order or hash mismatch")
            result = replay.commit(request, timestamp=datetime.fromisoformat(env["record"]["timestamp"]))
            if result != env:
                raise ActionError("Replay provenance mismatch")
        if digest(replay.scenario(sid)) != digest(self.scenario(sid)):
            raise ActionError("Replay overlay mismatch")
        return replay
