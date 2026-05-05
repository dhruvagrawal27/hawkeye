"""SQLAlchemy ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"

    id = Column(String, primary_key=True)  # employee_id
    account_id = Column(String, index=True)
    department = Column(String, nullable=True)
    role = Column(String, nullable=True)
    join_date = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, server_default=func.now(), onupdate=func.now())
    risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

    alerts = relationship("Alert", back_populates="employee")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String, ForeignKey("employees.id"), index=True)
    account_id = Column(String, nullable=True)
    score = Column(Float, nullable=False)
    m1_score = Column(Float, nullable=True)
    m2_score = Column(Float, nullable=True)
    threshold = Column(Float, nullable=False)
    severity = Column(String, nullable=False)  # low / medium / high / critical
    risk_factors = Column(JSON, nullable=True)  # top SHAP factors
    status = Column(String, default="open")  # open / in_review / resolved / false_positive
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    employee = relationship("Employee", back_populates="alerts")
    narrative = relationship("Narrative", back_populates="alert", uselist=False)


class Narrative(Base):
    __tablename__ = "narratives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), index=True)
    model_version = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    shap_footer = Column(Text, nullable=True)
    generated_at = Column(DateTime, server_default=func.now())
    token_usage = Column(JSON, nullable=True)

    alert = relationship("Alert", back_populates="narrative")


class TriageAction(Base):
    __tablename__ = "triage_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), index=True)
    action_type = Column(String, nullable=False)  # escalate / dismiss / investigate
    performed_by = Column(String, nullable=False)  # user sub
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_sub = Column(String, nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
