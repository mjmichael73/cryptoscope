"""initial write-side schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-11 09:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "watchlists",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("symbols", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.UniqueConstraint("tenant_id", "name", name="uq_watchlist_tenant_name"),
    )
    op.create_index("ix_watchlist_tenant", "watchlists", ["tenant_id"])

    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("comparator", sa.String(length=8), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index(
        "ix_alert_rule_tenant_symbol", "alert_rules", ["tenant_id", "symbol"]
    )

    op.create_table(
        "processed_commands",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("idempotency_key", sa.String(length=128), primary_key=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("processed_commands")
    op.drop_index("ix_alert_rule_tenant_symbol", table_name="alert_rules")
    op.drop_table("alert_rules")
    op.drop_index("ix_watchlist_tenant", table_name="watchlists")
    op.drop_table("watchlists")
    op.drop_table("tenants")
