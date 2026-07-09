"""FastAPI dependencies for tenant resolution."""

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
