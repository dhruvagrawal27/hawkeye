"""Health and readiness endpoints."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request
from app.schemas import HealthResponse

log = structlog.get_logger()
router = APIRouter()


@router.get("/healthz", response_model=HealthResponse, tags=["health"])
async def healthz():
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=HealthResponse, tags=["health"])
async def readyz(request: Request):
    services: dict[str, str] = {}

    # Check scoring loaded
    scoring = getattr(request.app.state, "scoring", None)
    services["scoring"] = "ok" if scoring and scoring.loaded else "not_loaded"

    # Check graph
    graph = getattr(request.app.state, "graph", None)
    services["graph"] = "ok" if graph and graph.connected else "not_connected"

    # Consumer stats
    consumer = getattr(request.app.state, "consumer", None)
    if consumer:
        services["consumer_events"] = str(consumer._events_consumed)
        services["consumer_alerts"] = str(consumer._alerts_created)

    all_ok = all(v in ("ok",) or k.startswith("consumer_") for k, v in services.items())
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        services=services,
    )
