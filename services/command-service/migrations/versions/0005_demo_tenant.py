"""seed demo tenant

Revision ID: 0005_demo_tenant
Revises: 0004_alert_rule_params
Create Date: 2026-11-15 15:40:00.000000

Inserts the fixed demo tenant that the Keycloak demo user's ``tenant_id``
claim maps to. The UUID must stay in sync with the claim mapper in
``deploy/keycloak/realm-export.json``.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_demo_tenant"
down_revision: str | None = "0004_alert_rule_params"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_TENANT_ID = "11111111-2222-3333-4444-555555555555"


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO tenants (id, slug, name, created_at) "
            "VALUES (CAST(:id AS uuid), :slug, :name, NOW()) "
            "ON CONFLICT (id) DO NOTHING"
        ).bindparams(id=DEMO_TENANT_ID, slug="demo", name="Demo Tenant")
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM tenants WHERE id = :id").bindparams(id=DEMO_TENANT_ID)
    )
