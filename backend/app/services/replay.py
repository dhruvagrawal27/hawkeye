"""Kafka replay service — reads JSONL and publishes to hawkeye.events."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import structlog

from app.config import get_settings
from app.schemas import ReplayStatus

log = structlog.get_logger()
settings = get_settings()


class ReplayService:
    def __init__(self) -> None:
        self._running = False
        self._paused = False
        self._rate = settings.replay_default_rate
        self._events_published = 0
        self._task: asyncio.Task | None = None
        self._producer = None

    def _get_producer(self):
        if self._producer is not None:
            return self._producer
        try:
            from confluent_kafka import Producer
            self._producer = Producer({
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "linger.ms": 5,
                "batch.size": 65536,
            })
            return self._producer
        except Exception as exc:
            log.warning("kafka_producer_failed", error=str(exc))
            return None

    async def start(self, rate: int = 50) -> None:
        if self._running:
            self._rate = rate
            return
        self._rate = min(rate, settings.replay_max_rate)
        self._running = True
        self._paused = False
        self._task = asyncio.create_task(self._replay_loop())
        log.info("replay_started", rate=self._rate)

    def stop(self) -> None:
        self._running = False
        self._paused = False
        if self._task:
            self._task.cancel()
        log.info("replay_stopped", published=self._events_published)

    def pause(self) -> None:
        self._paused = not self._paused
        log.info("replay_paused" if self._paused else "replay_resumed")

    async def _replay_loop(self) -> None:
        path = Path(settings.replay_events_path)
        if not path.exists():
            log.warning("replay_file_missing", path=str(path))
            self._running = False
            return

        producer = self._get_producer()
        interval = 1.0 / self._rate if self._rate > 0 else 0.02

        while self._running:
            with open(path) as f:
                for line in f:
                    if not self._running:
                        return
                    while self._paused:
                        await asyncio.sleep(0.1)

                    line = line.strip()
                    if not line:
                        continue

                    interval = 1.0 / self._rate if self._rate > 0 else 0.02

                    if producer:
                        try:
                            producer.produce(
                                settings.kafka_topic,
                                value=line.encode(),
                                callback=self._delivery_callback,
                            )
                            producer.poll(0)
                            self._events_published += 1
                        except Exception as exc:
                            log.warning("produce_failed", error=str(exc))

                    await asyncio.sleep(interval)

            log.info("replay_loop_complete", published=self._events_published)
            # Loop back to beginning

    def _delivery_callback(self, err, msg):
        if err:
            log.warning("kafka_delivery_failed", error=str(err))

    def status(self) -> ReplayStatus:
        return ReplayStatus(
            running=self._running,
            paused=self._paused,
            rate=self._rate,
            events_published=self._events_published,
            events_consumed=0,
            alerts_created=0,
        )
