"""Kafka event consumer — FastAPI background task."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.services.scoring import ScoringService
from app.services.graph_service import GraphService
from app.services.feature_aggregator import FeatureAggregator
from app.services.replay import ReplayService

log = structlog.get_logger()
settings = get_settings()

_SEVERITY_THRESHOLDS = {
    "low": 0.0,
    "medium": 0.5,
    "high": 0.7,
    "critical": 0.9,
}


def _score_to_severity(score: float) -> str:
    if score >= 0.9:
        return "critical"
    if score >= 0.7:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


class EventConsumer:
    def __init__(
        self,
        scoring_service: ScoringService,
        graph_service: GraphService,
    ) -> None:
        self._scoring = scoring_service
        self._graph = graph_service
        self._running = False
        self._consumer = None
        self._redis = None
        self._agg: FeatureAggregator | None = None
        self._events_consumed = 0
        self._alerts_created = 0
        self._last_score_time: dict[str, float] = {}
        self.replay_service = ReplayService()

    def stop(self) -> None:
        self._running = False

    async def run(self) -> None:
        self._running = True
        from app.deps import get_redis
        self._redis = await get_redis()
        self._agg = FeatureAggregator(self._redis)

        # Wait for Kafka to be ready
        await asyncio.sleep(5)

        consumer = self._get_consumer()
        if consumer is None:
            log.warning("consumer_unavailable_no_kafka")
            return

        log.info("consumer_started")
        loop = asyncio.get_event_loop()
        try:
            while self._running:
                # Run blocking poll() in executor so asyncio event loop is not frozen
                msg = await loop.run_in_executor(None, consumer.poll, 1.0)
                if msg is None:
                    continue
                if msg.error():
                    log.warning("kafka_consumer_error", error=str(msg.error()))
                    continue
                try:
                    event = json.loads(msg.value().decode())
                    await self._process_event(event)
                    self._events_consumed += 1
                    if self._events_consumed % 500 == 0:
                        log.info("consumer_progress",
                                 events=self._events_consumed,
                                 alerts=self._alerts_created)
                except Exception as exc:
                    log.warning("event_process_failed", error=str(exc))
        finally:
            consumer.close()
            log.info("consumer_stopped")

    def _get_consumer(self):
        try:
            from confluent_kafka import Consumer
            c = Consumer({
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "group.id": settings.kafka_group_id,
                "auto.offset.reset": "latest",
                "enable.auto.commit": True,
            })
            c.subscribe([settings.kafka_topic])
            return c
        except Exception as exc:
            log.warning("consumer_init_failed", error=str(exc))
            return None

    async def _process_event(self, event: dict[str, Any]) -> None:
        # Insider-threat overlay: map account_id → employee_id
        employee_id = event.get("employee_id") or event.get("account_id", "unknown")
        resource_id = event.get("system_resource") or event.get("counterparty_id", "unknown")

        # Update Neo4j graph
        await self._graph.merge_access(employee_id, resource_id, event)

        # Update Redis aggregates
        assert self._agg is not None
        await self._agg.update(employee_id, event)

        # Check if we should score this employee
        event_count = await self._agg.get_event_count(employee_id)
        now = time.time()
        last_scored = self._last_score_time.get(employee_id, 0)
        should_score = (
            event_count % settings.score_trigger_every_n_events == 0
            or (now - last_scored) >= settings.score_trigger_every_n_seconds
        )

        if should_score:
            await self._score_employee(employee_id, event)
            self._last_score_time[employee_id] = now

    async def _score_employee(self, employee_id: str, trigger_event: dict[str, Any]) -> None:
        assert self._agg is not None
        features = await self._agg.get_features(employee_id)
        result = self._scoring.score(features)
        score = result["score"]

        # Update graph risk score
        await self._graph.update_risk_score(employee_id, score)

        # Create alert if above threshold (deduplicated)
        if result["is_alert"]:
            await self._maybe_create_alert(employee_id, result, trigger_event)

    async def _maybe_create_alert(
        self,
        employee_id: str,
        score_result: dict[str, Any],
        event: dict[str, Any],
    ) -> None:
        # Deduplication: check Redis for recent alert
        dedup_key = f"hawkeye:alert_dedup:{employee_id}"
        exists = await self._redis.get(dedup_key)
        if exists:
            return

        # Write alert to Postgres
        try:
            from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
            from app.models import Alert, Employee
            from app.config import get_settings

            cfg = get_settings()
            engine = create_async_engine(cfg.database_url, pool_pre_ping=True)
            factory = async_sessionmaker(engine, expire_on_commit=False)

            async with factory() as session:
                # Upsert employee
                emp = await session.get(Employee, employee_id)
                if not emp:
                    emp = Employee(
                        id=employee_id,
                        account_id=event.get("account_id", employee_id),
                        department=event.get("department"),
                        role=event.get("access_type"),
                    )
                    session.add(emp)
                emp.risk_score = score_result["score"]
                emp.last_seen = datetime.now(timezone.utc)

                alert = Alert(
                    employee_id=employee_id,
                    account_id=event.get("account_id", employee_id),
                    score=score_result["score"],
                    m1_score=score_result["m1"],
                    m2_score=score_result["m2"],
                    threshold=score_result["threshold"],
                    severity=_score_to_severity(score_result["score"]),
                    risk_factors=score_result["top_factors"],
                    status="open",
                )
                session.add(alert)
                await session.commit()
                await session.refresh(alert)

                self._alerts_created += 1
                log.info(
                    "alert_created",
                    employee_id=employee_id,
                    score=score_result["score"],
                    alert_id=str(alert.id),
                )

                # Broadcast via WebSocket
                from app.ws.alerts import alert_broadcaster
                await alert_broadcaster.broadcast({
                    "type": "alert",
                    "id": str(alert.id),
                    "employee_id": employee_id,
                    "score": score_result["score"],
                    "severity": alert.severity,
                    "created_at": alert.created_at.isoformat(),
                    "risk_factors": score_result["top_factors"],
                })

            await engine.dispose()
        except Exception as exc:
            log.warning("alert_write_failed", error=str(exc))
            return

        # Set dedup key
        await self._redis.setex(
            dedup_key,
            settings.alert_dedup_window_seconds,
            "1",
        )
