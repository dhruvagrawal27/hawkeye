"""FastAPI dependency factories."""

from __future__ import annotations

from typing import AsyncGenerator

import redis.asyncio as aioredis
from neo4j import AsyncGraphDatabase, AsyncDriver
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import get_settings

settings = get_settings()

# ── SQLAlchemy ────────────────────────────────────────────────────────────────
_engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Redis ─────────────────────────────────────────────────────────────────────
_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


# ── Neo4j ─────────────────────────────────────────────────────────────────────
_neo4j_driver: AsyncDriver | None = None


async def get_neo4j() -> AsyncDriver:
    global _neo4j_driver
    if _neo4j_driver is None:
        _neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _neo4j_driver


async def close_neo4j() -> None:
    global _neo4j_driver
    if _neo4j_driver:
        await _neo4j_driver.close()
        _neo4j_driver = None
