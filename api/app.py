"""Same-origin local API. No arbitrary path, URL proxy or direct graph mutation endpoints."""

from __future__ import annotations

import hmac
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from urbanimpact.actions import ActionError
from urbanimpact.contracts import MANIFEST, ActionRequest, CityPack, Scenario
from urbanimpact.fixtures import toy_city

from .services import RunService


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    citypack_id: str = Field(min_length=1, max_length=160)
    scenario_id: str = Field(min_length=1, max_length=160)


class BodyLimit:
    def __init__(self, app, max_bytes=16 * 1024 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                return await JSONResponse(
                    {"code": "PAYLOAD_TOO_LARGE", "message": "Request exceeds local limit"}, status_code=413
                )(scope, receive, send)
            if not message.get("more_body", False):
                break
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        return await self.app(scope, replay, send)


def create_app(root: Path | None = None, cities=None, policy_backend=None):
    root = root or Path(os.environ.get("CIVIFLUX_WORKSPACE", ".runtime/app"))
    if cities is None:
        cities = [toy_city()]
        real = Path("data/citypacks/helsinki-current/citypack.json")
        if real.is_file() and os.environ.get("CIVIFLUX_TOY_ONLY") != "1":
            cities.append(CityPack.model_validate_json(real.read_bytes()))
    if policy_backend is None:
        from adapters.system_one.simplejev import SimpleJevBackend, SimpleJevConfig

        policy_backend = SimpleJevBackend(
            SimpleJevConfig.from_env(Path(".env"), ontology_version=MANIFEST["ontology_version"])
        )
    service = RunService(root, cities, policy_backend)
    token = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app):
        yield
        service.close()

    app = FastAPI(title="CiviFlux local scenario API", version="0.1.0", lifespan=lifespan)
    app.state.service = service
    app.state.token = token
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver", "[::1]"])
    app.add_middleware(BodyLimit)

    @app.middleware("http")
    async def security(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
            return JSONResponse(
                {"code": "CROSS_ORIGIN_DENIED", "message": "Same-origin API required"}, status_code=403
            )
        if request.url.path.startswith("/api/") and request.headers.get("sec-fetch-site") in (
            "cross-site",
            "same-site",
        ):
            return JSONResponse(
                {"code": "CROSS_ORIGIN_DENIED", "message": "Same-origin API required"}, status_code=403
            )
        public = {"/api/v1/health", "/api/v1/session"}
        if request.url.path.startswith("/api/") and request.url.path not in public:
            supplied = request.headers.get("authorization", "")
            if not hmac.compare_digest(supplied, "Bearer " + token):
                return JSONResponse(
                    {"code": "UNAUTHORIZED", "message": "Local session token required"}, status_code=401
                )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; worker-src 'self' blob:; connect-src 'self'; frame-ancestors 'self'; object-src 'none'"
        )
        return response

    @app.exception_handler(ActionError)
    async def action_error(request, exc):
        return JSONResponse(
            {
                "code": "INVALID_ACTION",
                "message": str(exc),
                "stage": "validation",
                "retryable": False,
                "details_redacted": True,
            },
            status_code=409,
        )

    @app.exception_handler(KeyError)
    async def key_error(request, exc):
        return JSONResponse(
            {"code": "NOT_FOUND", "message": "Unknown resource", "retryable": False}, status_code=404
        )

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "version": "0.1.0", "ontology_version": MANIFEST["ontology_version"]}

    @app.get("/api/v1/session")
    def session():
        return {"token": token}

    @app.get("/api/v1/capabilities")
    def capabilities():
        config = getattr(policy_backend, "config", None)
        return {
            "routing": True,
            "sumo": True,
            "ranking": ["A0", "A1", "A2", "A3", "A4", "A5"],
            "qwen": {
                "mode": getattr(config, "provider_mode", "unconfigured"),
                "configured": bool(config and getattr(config, "ready", False)),
                "status": "AVAILABLE" if config and getattr(config, "ready", False) else "BLOCKED_API_SETUP",
            },
            "measured_prediction": "NOT_VALIDATED",
            "max_parallel_jobs": 1,
        }

    @app.get("/api/v1/ontology")
    def ontology():
        return MANIFEST

    @app.get("/api/v1/citypacks")
    def citypacks():
        return [
            {
                "citypack_id": c.citypack_id,
                "network_temporality": c.network_temporality,
                "transit_temporality": c.transit_temporality,
                "warnings": c.warnings,
                "edge_count": len(c.edges),
                "facility_count": len(c.facilities),
            }
            for c in service.cities.values()
        ]

    @app.post("/api/v1/citypacks/import", status_code=201)
    def import_citypack(city: CityPack):
        if city.citypack_id in service.cities:
            raise ActionError("Citypack ID already registered")
        from urbanimpact.actions import Workspace
        from urbanimpact.util import atomic_json, digest

        service.cities[city.citypack_id] = city
        service.workspaces[city.citypack_id] = Workspace(
            root / "workspaces" / (digest(city.citypack_id) + ".sqlite"), city
        )
        atomic_json(root / "imports" / (digest(city.citypack_id) + ".json"), city)
        return {"citypack_id": city.citypack_id, "source_snapshot_hash": digest(city)}

    @app.get("/api/v1/citypacks/{cid}/scenario-template")
    def template(cid: str):
        return service.template(cid)

    @app.get("/api/v1/citypacks/{cid}")
    def geometry(cid: str):
        city = service.cities[cid]
        features = [
            {
                "type": "Feature",
                "id": e.id,
                "properties": {"id": e.id, "type": "RoadSegment", "name": e.name},
                "geometry": {"type": "LineString", "coordinates": e.geometry},
            }
            for e in city.edges
            if len(e.geometry) > 1
        ]
        features.extend(
            {
                "type": "Feature",
                "id": f.id,
                "properties": {"id": f.id, "type": f.type, "name": f.name, "access_status": f.access_status},
                "geometry": {"type": "Point", "coordinates": [f.lon, f.lat]},
            }
            for f in city.facilities
        )
        geo = {"type": "FeatureCollection", "features": features}
        return {
            "citypack_id": cid,
            "network_temporality": city.network_temporality,
            "transit_temporality": city.transit_temporality,
            "warnings": city.warnings,
            "geojson": geo,
            **geo,
        }

    @app.post("/api/v1/scenarios/validate")
    def validate(s: Scenario):
        return service.workspace(s.citypack_id).validate_scenario(s)

    @app.post("/api/v1/actions/validate")
    def validate_action(a: ActionRequest):
        return service.action(a, True)

    @app.post("/api/v1/actions", status_code=201)
    def action(a: ActionRequest):
        return service.action(a)

    @app.get("/api/v1/scenarios/{sid}/actions")
    def history(sid: str):
        return service.find_workspace(sid).history(sid)

    @app.post("/api/v1/runs", status_code=202)
    def run(r: RunRequest, idempotency_key: Annotated[str | None, Header(max_length=160)] = None):
        return service.submit(r.citypack_id, r.scenario_id, idempotency_key)

    @app.get("/api/v1/runs/{rid}")
    def state(rid: str):
        return service.state(rid)

    @app.post("/api/v1/runs/{rid}/cancel")
    def cancel(rid: str):
        return service.cancel(rid)

    @app.get("/api/v1/runs/{rid}/results")
    def result(rid: str):
        return service.result(rid)

    @app.get("/api/v1/runs/{rid}/export")
    def export(rid: str):
        return FileResponse(service.export(rid), filename=rid + ".zip", media_type="application/zip")

    @app.get("/api/v1/objects/{oid:path}")
    def object_view(oid: str, citypack_id: str, scenario_id: str | None = None, run_id: str | None = None):
        return service.object_view(oid, citypack_id, scenario_id, run_id)

    @app.api_route("/api/{unmatched:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    def unknown_api(unmatched: str):
        return JSONResponse({"code": "NOT_FOUND", "message": "Unknown API endpoint"}, status_code=404)

    dist = Path("web/dist")
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app
