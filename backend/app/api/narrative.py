"""Narrative API endpoints."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_analyst, require_supervisor
from app.deps import get_db
from app.models import Alert, Narrative
from app.schemas import NarrativeRead

router = APIRouter()


@router.get("/{alert_id}", response_model=NarrativeRead)
async def get_narrative(
    alert_id: uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_analyst),
):
    # Return cached narrative if exists
    result = await db.execute(
        select(Narrative).where(Narrative.alert_id == alert_id).order_by(
            Narrative.generated_at.desc()
        ).limit(1)
    )
    narrative = result.scalar_one_or_none()
    if narrative:
        return narrative

    # Generate on demand
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    from app.services.narrative import NarrativeService
    svc = NarrativeService()
    narrative = await svc.generate(alert, db)
    return narrative


@router.post("/{alert_id}/regenerate", response_model=NarrativeRead)
async def regenerate_narrative(
    alert_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_supervisor),
):
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    from app.services.narrative import NarrativeService
    svc = NarrativeService()
    narrative = await svc.generate(alert, db, force=True)
    return narrative
