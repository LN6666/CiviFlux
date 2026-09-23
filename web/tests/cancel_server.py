"""Browser-only API host that holds one real RunService job for cancellation assertions.

This process is started only by Playwright on loopback. It does not replace any
product endpoint or fabricate a result: after the test releases the gate, the
normal analysis method runs and observes the RunService cancellation event.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Event

import uvicorn
from fastapi.routing import APIRoute
from urbanimpact.fixtures import toy_city

from api.app import create_app

started = Event()
release = Event()
app = create_app(
    root=Path(os.environ.get("CIVIFLUX_WORKSPACE", ".runtime/browser-cancel")),
    cities=[toy_city()],
)
service = app.state.service
normal_run = service.analysis.run


def held_run(*args, **kwargs):
    kwargs["stage"]("browser_test_waiting_for_cancel")
    started.set()
    if not release.wait(20):
        raise TimeoutError("Browser cancellation gate was not released")
    return normal_run(*args, **kwargs)


service.analysis.run = held_run


def state():
    return {"started": started.is_set(), "released": release.is_set()}


def release_run():
    release.set()
    return {"released": True}


def reset_gate():
    started.clear()
    release.clear()
    return {"started": False, "released": False}


# create_app mounts static files last; insert browser-only controls before it.
app.router.routes.insert(0, APIRoute("/__browser_test__/state", state, methods=["GET"]))
app.router.routes.insert(1, APIRoute("/__browser_test__/release", release_run, methods=["POST"]))
app.router.routes.insert(2, APIRoute("/__browser_test__/reset", reset_gate, methods=["POST"]))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8767, access_log=False)
