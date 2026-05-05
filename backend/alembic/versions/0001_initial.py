"""Initial migration — create all tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("account_id", sa.String, nullable=True),
        sa.Column("department", sa.String, nullable=True),
        sa.Column("role", sa.String, nullable=True),
        sa.Column("join_date", sa.DateTime, nullable=True),
        sa.Column("last_seen", sa.DateTime, server_default=sa.func.now()),
        sa.Column("risk_score", sa.Float, default=0.0),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_employees_account_id", "employees", ["account_id"])

    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", sa.String, sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("account_id", sa.String, nullable=True),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("m1_score", sa.Float, nullable=True),
        sa.Column("m2_score", sa.Float, nullable=True),
        sa.Column("threshold", sa.Float, nullable=False),
        sa.Column("severity", sa.String, nullable=False),
        sa.Column("risk_factors", sa.JSON, nullable=True),
        sa.Column("status", sa.String, default="open"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_alerts_employee_id", "alerts", ["employee_id"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])

    op.create_table(
        "narratives",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_id", UUID(as_uuid=True), sa.ForeignKey("alerts.id")),
        sa.Column("model_version", sa.String, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("shap_footer", sa.Text, nullable=True),
        sa.Column("generated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("token_usage", sa.JSON, nullable=True),
    )

    op.create_table(
        "triage_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_id", UUID(as_uuid=True), sa.ForeignKey("alerts.id")),
        sa.Column("action_type", sa.String, nullable=False),
        sa.Column("performed_by", sa.String, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_sub", sa.String, nullable=True),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("resource_type", sa.String, nullable=True),
        sa.Column("resource_id", sa.String, nullable=True),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("ip_address", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("triage_actions")
    op.drop_table("narratives")
    op.drop_table("alerts")
    op.drop_table("employees")
