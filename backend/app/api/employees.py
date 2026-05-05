"""Employees API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_analyst
from app.deps import get_db
from app.models import Alert, Employee
from app.schemas import AlertRead, EmployeeRead

router = APIRouter()


@router.get("", response_model=list[EmployeeRead])
async def list_employees(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_analyst),
    limit: int = 100,
):
    result = await db.execute(
        select(Employee).order_by(desc(Employee.risk_score)).limit(limit)
    )
    return result.scalars().all()


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_analyst),
):
    emp = await db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@router.get("/{employee_id}/alerts", response_model=list[AlertRead])
async def get_employee_alerts(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_analyst),
):
    result = await db.execute(
        select(Alert)
        .where(Alert.employee_id == employee_id)
        .order_by(desc(Alert.created_at))
        .limit(50)
    )
    return result.scalars().all()
