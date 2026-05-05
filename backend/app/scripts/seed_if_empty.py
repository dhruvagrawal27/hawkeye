"""Seed script — loads model artifacts + synthetic data into all stores."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import structlog

log = structlog.get_logger()


async def seed_if_empty() -> None:
    from app.config import get_settings
    from app.deps import get_neo4j

    settings = get_settings()

    # ── Alembic migrations (idempotent) ──────────────────────────────────────
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(str(Path(__file__).parent.parent.parent / "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
        log.info("alembic_migrations_ok")
    except Exception as exc:
        log.warning("alembic_failed", error=str(exc))

    # ── Neo4j seed ────────────────────────────────────────────────────────────
    txns_path = Path(settings.replay_events_path).parent / "synthetic_transactions.parquet"
    accts_path = Path(settings.replay_events_path).parent / "synthetic_accounts.parquet"
    if txns_path.exists():
        from app.services.graph_service import GraphService
        gs = GraphService()
        await gs.connect()
        await gs.seed_from_synthetic(str(accts_path), str(txns_path))

    # ── MinIO artifact upload ─────────────────────────────────────────────────
    try:
        from minio import Minio
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=False,
        )
        bucket = settings.minio_bucket
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        artifacts_dir = Path(settings.model_m1_path).parent
        for f in artifacts_dir.glob("*.txt"):
            client.fput_object(bucket, f.name, str(f))
            log.info("minio_upload", file=f.name)
    except Exception as exc:
        log.warning("minio_upload_failed", error=str(exc))

    log.info("seed_complete")


if __name__ == "__main__":
    asyncio.run(seed_if_empty())
