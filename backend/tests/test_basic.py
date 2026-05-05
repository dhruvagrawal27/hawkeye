"""Backend tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_healthz():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_score_service_stub():
    """Scoring service returns a sensible dict even when models are missing."""
    from app.services.scoring import ScoringService
    svc = ScoringService()
    result = svc.score({"n": 10, "sa": 1000.0})
    assert "score" in result
    assert "threshold" in result
    assert isinstance(result["top_factors"], list)
