"""Dev-only scoring endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from app.auth import require_analyst
from app.deps import get_redis
from app.schemas import ScoreRequest, ScoreResponse
from app.services.feature_aggregator import FeatureAggregator

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


@router.get("/score/employee/{employee_id}", tags=["scoring"])
async def score_employee(
    employee_id: str,
    request: Request,
    _auth=Depends(require_analyst),
    redis=Depends(get_redis),
):
    """Debug: fetch live features from Redis and score an employee."""
    agg = FeatureAggregator(redis)
    features = await agg.get_features(employee_id)
    scoring = request.app.state.scoring
    result = scoring.score(features)
    return {
        "employee_id": employee_id,
        "features": features,
        "scoring_loaded": scoring.loaded,
        **result,
    }
