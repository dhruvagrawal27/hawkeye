"""Pydantic schemas for API request/response."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class RiskFactor(BaseModel):
    feature: str
    contribution: float
    plain_name: str


class AlertBase(BaseModel):
    employee_id: str
    score: float
    severity: str
    risk_factors: list[RiskFactor] = []


class AlertCreate(AlertBase):
    account_id: str | None = None
    m1_score: float | None = None
    m2_score: float | None = None
    threshold: float = 0.5


class AlertRead(AlertBase):
    id: uuid.UUID
    account_id: str | None = None
    m1_score: float | None = None
    m2_score: float | None = None
    threshold: float
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NarrativeRead(BaseModel):
    id: uuid.UUID
    alert_id: uuid.UUID
    model_version: str
    content: str
    shap_footer: str | None = None
    generated_at: datetime

    model_config = {"from_attributes": True}


class EmployeeRead(BaseModel):
    id: str
    account_id: str | None = None
    department: str | None = None
    role: str | None = None
    risk_score: float
    last_seen: datetime | None = None

    model_config = {"from_attributes": True}


class ScoreRequest(BaseModel):
    features: dict[str, Any]
    employee_id: str | None = None


class ScoreResponse(BaseModel):
    score: float
    m1: float
    m2: float
    top_factors: list[RiskFactor]
    threshold: float
    is_alert: bool


class ReplayRequest(BaseModel):
    action: str  # start | stop | pause
    rate: int | None = None


class ReplayStatus(BaseModel):
    running: bool
    paused: bool
    rate: int
    events_published: int
    events_consumed: int
    alerts_created: int


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # employee | system
    risk_score: float | None = None
    flagged: bool = False


class GraphLink(BaseModel):
    source: str
    target: str
    weight: float = 1.0
    access_type: str | None = None


class GraphData(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]


class TriageActionCreate(BaseModel):
    action_type: str
    notes: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    services: dict[str, str] = Field(default_factory=dict)
