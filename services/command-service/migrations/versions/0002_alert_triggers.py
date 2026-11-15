"""add alert_triggers table for the alert service

Revision ID: 0002_alert_triggers
Revises: 0001_initial
Create Date: 2026-06-27 11:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_alert_triggers"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alert_triggers",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("comparator", sa.String(length=8), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["rule_id"], ["alert_rules.id"]),
    )
    op.create_index("ix_alert_trigger_tenant", "alert_triggers", ["tenant_id"])
    op.create_index(
        "ix_alert_trigger_tenant_rule", "alert_triggers", ["tenant_id", "rule_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_alert_trigger_tenant_rule", table_name="alert_triggers")
    op.drop_index("ix_alert_trigger_tenant", table_name="alert_triggers")
    op.drop_table("alert_triggers")
