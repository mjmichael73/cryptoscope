"""alert rule params: interval, window_seconds, cooldown_seconds, wider comparator

Revision ID: 0004_alert_rule_params
Revises: 0003_add_alert_rule_status
Create Date: 2026-08-30 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_alert_rule_params"
down_revision: str | None = "0003_add_alert_rule_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The comparator vocabulary grew beyond above/below (crossing, percent
    # change, RSI); "pct_change_above" needs 16 characters.
    op.alter_column(
        "alert_rules",
        "comparator",
        existing_type=sa.String(length=8),
        type_=sa.String(length=32),
    )
    op.add_column(
        "alert_rules",
        sa.Column("interval", sa.String(length=8), nullable=False, server_default="1m"),
    )
    op.add_column("alert_rules", sa.Column("window_seconds", sa.Integer(), nullable=True))
    op.add_column(
        "alert_rules",
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="300"),
    )
    # Triggers record the evaluation context so notifications and the history
    # dashboard can show which interval and window produced the alert.
    op.add_column(
        "alert_triggers",
        sa.Column("interval", sa.String(length=8), nullable=False, server_default="1m"),
    )
    op.add_column("alert_triggers", sa.Column("window_seconds", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("alert_triggers", "window_seconds")
    op.drop_column("alert_triggers", "interval")
    op.drop_column("alert_rules", "cooldown_seconds")
    op.drop_column("alert_rules", "window_seconds")
    op.drop_column("alert_rules", "interval")
    op.alter_column(
        "alert_rules",
        "comparator",
        existing_type=sa.String(length=32),
        type_=sa.String(length=8),
    )
