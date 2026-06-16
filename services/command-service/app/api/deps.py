"""FastAPI dependencies for tenant resolution and idempotency.

In production the gateway validates the Keycloak token and forwards the tenant
id and slug as trusted headers. The command service reads those headers, binds
the tenant to the request context, and rejects requests that lack them.
"""

from __future__ import annotations

from cryptoscope_shared.tenant import TenantIdentity, set_tenant
from fastapi import Header, HTTPException, status


async def require_tenant(
    x_tenant_id: str = Header(default=""),
    x_tenant_slug: str = Header(default=""),
) -> TenantIdentity:
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing tenant identity",
        )
    identity = TenantIdentity(id=x_tenant_id, slug=x_tenant_slug)
    set_tenant(identity)
    return identity


async def require_idempotency_key(
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
) -> str:
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing Idempotency-Key header",
        )
    return idempotency_key
