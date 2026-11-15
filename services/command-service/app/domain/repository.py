"""Write-side repository port.

The application service depends on this narrow interface rather than on a
concrete database. That keeps the use cases unit testable with an in-memory
fake and lets the SQLAlchemy adapter live entirely in the infra layer.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.models import AlertRule, Watchlist


class WriteRepository(Protocol):
    async def resource_for_key(self, tenant_id: str, key: str) -> str | None:
        """Return the resource id a prior command with this key produced."""
        ...

    async def add_watchlist(self, watchlist: Watchlist) -> None: ...

    async def add_alert_rule(self, rule: AlertRule) -> None: ...

    async def record_command(self, tenant_id: str, key: str, resource_id: str) -> None:
        ...

    async def commit(self) -> None: ...

    async def list_watchlists(self, tenant_id: str) -> list[Watchlist]: ...

    async def get_watchlist(self, tenant_id: str, watchlist_id: str) -> Watchlist | None:
        ...

    async def update_watchlist(self, watchlist: Watchlist) -> None: ...

    async def delete_watchlist(self, watchlist: Watchlist) -> None: ...

    async def get_alert_rule(self, tenant_id: str, rule_id: str) -> AlertRule | None:
        ...

    async def soft_delete_alert_rule(self, rule: AlertRule) -> None: ...
