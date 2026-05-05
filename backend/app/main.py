"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import structlog
import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.config import get_settings
from app.deps import close_neo4j
from app.services.scoring import ScoringService
from app.services.graph_service import GraphService
from app.consumers.event_consumer import EventConsumer
from app.ws.alerts import alert_broadcaster

from app.api.health import router as health_router
from app.api.alerts import router as alerts_router
from app.api.employees import router as employees_router
from app.api.graph import router as graph_router
from app.api.narrative import router as narrative_router
from app.api.replay import router as replay_router
from app.ws.alerts import router as ws_router

settings = get_settings()
log = structlog.get_logger()

# Sentry (no-op if DSN is empty or not a valid URL)
if settings.sentry_dsn and settings.sentry_dsn.startswith("http"):
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

# Scoring + graph service singletons
_scoring_service: ScoringService | None = None
_graph_service: GraphService | None = None
_consumer: EventConsumer | None = None
_consumer_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scoring_service, _graph_service, _consumer, _consumer_task
    log.info("hawkeye_startup")

    # Load scoring models
    _scoring_service = ScoringService()
    await _scoring_service.load()
    app.state.scoring = _scoring_service

    # Graph service
    _graph_service = GraphService()
    await _graph_service.connect()
    app.state.graph = _graph_service

    # Start Kafka consumer as background task
    _consumer = EventConsumer(
        scoring_service=_scoring_service,
        graph_service=_graph_service,
    )
    _consumer_task = asyncio.create_task(_consumer.run())
    app.state.consumer = _consumer

    log.info("hawkeye_ready")
    yield

    log.info("hawkeye_shutdown")
    if _consumer:
        _consumer.stop()
    if _consumer_task:
        _consumer_task.cancel()
    await close_neo4j()


app = FastAPI(
    title="HAWKEYE",
    description="Insider-threat early-warning system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Routers
app.include_router(health_router)
app.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
app.include_router(employees_router, prefix="/employees", tags=["employees"])
app.include_router(graph_router, prefix="/graph", tags=["graph"])
app.include_router(narrative_router, prefix="/narrative", tags=["narrative"])
app.include_router(replay_router, prefix="/events", tags=["replay"])
app.include_router(ws_router, prefix="/ws", tags=["websocket"])
