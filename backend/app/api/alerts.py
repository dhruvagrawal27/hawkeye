"""Alerts API endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_analyst, require_supervisor
from app.deps import get_db
from app.models import Alert, TriageAction
from app.schemas import AlertRead, TriageActionCreate
from app.ws.alerts import alert_broadcaster

router = APIRouter()


@router.get("", response_model=list[AlertRead])
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_analyst),
    limit: int = Query(100, le=500),
    offset: int = 0,
    status: str | None = None,
    severity: str | None = None,
):
    q = select(Alert).order_by(desc(Alert.created_at)).limit(limit).offset(offset)
    if status:
        q = q.where(Alert.status == status)
    if severity:
        q = q.where(Alert.severity == severity)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{alert_id}", response_model=AlertRead)
async def get_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_analyst),
):
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/{alert_id}/triage")
async def triage_alert(
    alert_id: uuid.UUID,
    body: TriageActionCreate,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_supervisor),
):
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    triage = TriageAction(
        alert_id=alert_id,
        action_type=body.action_type,
        performed_by=auth.get("sub", "unknown"),
        notes=body.notes,
    )
    db.add(triage)

    if body.action_type in ("dismiss", "false_positive"):
        alert.status = "false_positive"
    elif body.action_type == "escalate":
        alert.status = "in_review"
    elif body.action_type == "resolve":
        alert.status = "resolved"

    await db.commit()
    return {"status": "ok", "alert_status": alert.status}
