"""Dev-only scoring endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from app.auth import require_analyst
from app.schemas import ScoreRequest, ScoreResponse

router = APIRouter()


@router.post("/score", response_model=ScoreResponse, tags=["scoring"])
async def score_features(
    body: ScoreRequest,
    request: Request,
    _auth=Depends(require_analyst),
):
    scoring = request.app.state.scoring
    result = scoring.score(body.features)
    return ScoreResponse(**result)
