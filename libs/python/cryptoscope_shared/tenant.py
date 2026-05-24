"""Tenant context helpers for the Python services.

The tenant id scopes every tenant-owned query. We keep it in a context variable
so request handlers and repositories can read it without threading it through
every function signature.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


class MissingTenantError(RuntimeError):
    """Raised when a tenant is required but not present in the context."""


@dataclass(frozen=True)
class TenantIdentity:
    id: str
    slug: str = ""


_current_tenant: ContextVar[TenantIdentity | None] = ContextVar(
    "current_tenant", default=None
)


def set_tenant(identity: TenantIdentity) -> None:
    _current_tenant.set(identity)


def current_tenant() -> TenantIdentity:
    identity = _current_tenant.get()
    if identity is None or not identity.id:
        raise MissingTenantError("tenant identity is missing from context")
    return identity
