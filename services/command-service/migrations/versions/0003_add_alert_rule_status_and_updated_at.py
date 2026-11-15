"""add status and updated_at columns to alert_rules

Revision ID: 0003_add_alert_rule_status
Revises: 0002_alert_triggers
Create Date: 2026-07-25 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_alert_rule_status"
down_revision: str | None = "0002_alert_triggers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "alert_rules",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
    )
    op.add_column(
        "alert_rules",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_column("alert_rules", "updated_at")
    op.drop_column("alert_rules", "status")
