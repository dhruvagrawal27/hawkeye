"""Replay control API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, HTTPException
from app.auth import require_analyst
from app.schemas import ReplayRequest, ReplayStatus

router = APIRouter()


@router.post("/replay", response_model=ReplayStatus)
async def control_replay(
    body: ReplayRequest,
    request: Request,
    _auth=Depends(require_analyst),
):
    consumer = getattr(request.app.state, "consumer", None)
    if consumer is None:
        raise HTTPException(status_code=503, detail="Consumer not initialised")

    replay_svc = consumer.replay_service
    if body.action == "start":
        rate = body.rate or 50
        await replay_svc.start(rate=rate)
    elif body.action == "stop":
        replay_svc.stop()
    elif body.action == "pause":
        replay_svc.pause()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {body.action}")

    return replay_svc.status()


@router.get("/replay/status", response_model=ReplayStatus)
async def replay_status(
    request: Request,
    _auth=Depends(require_analyst),
):
    consumer = getattr(request.app.state, "consumer", None)
    if consumer is None:
        raise HTTPException(status_code=503, detail="Consumer not initialised")
    return consumer.replay_service.status()
