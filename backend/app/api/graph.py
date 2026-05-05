"""Graph API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Query
from app.auth import require_analyst
from app.schemas import GraphData

router = APIRouter()


@router.get("/{employee_id}", response_model=GraphData)
async def get_employee_graph(
    employee_id: str,
    request: Request,
    depth: int = Query(2, ge=1, le=3),
    _auth=Depends(require_analyst),
):
    graph_service = request.app.state.graph
    return await graph_service.get_neighborhood(employee_id, depth=depth)


@router.get("", response_model=GraphData)
async def get_global_graph(
    request: Request,
    limit: int = Query(50, le=200),
    _auth=Depends(require_analyst),
):
    """Return the top N highest-risk employees and their resource connections."""
    graph_service = request.app.state.graph
    return await graph_service.get_top_risk_graph(limit=limit)
