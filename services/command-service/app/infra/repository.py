"""SQLAlchemy backed WriteRepository.

Wraps a single AsyncSession as one unit of work: the writes accumulate and are
made durable together on commit, which keeps the idempotency ledger and the
resource row consistent.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import AlertRule, ProcessedCommand, Watchlist


class SqlAlchemyWriteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resource_for_key(self, tenant_id: str, key: str) -> str | None:
        result = await self._session.execute(
            select(ProcessedCommand.resource_id).where(
                ProcessedCommand.tenant_id == tenant_id,
                ProcessedCommand.idempotency_key == key,
            )
        )
        return result.scalar_one_or_none()

    async def add_watchlist(self, watchlist: Watchlist) -> None:
        self._session.add(watchlist)
        await self._session.flush()

    async def add_alert_rule(self, rule: AlertRule) -> None:
        self._session.add(rule)
        await self._session.flush()

    async def record_command(self, tenant_id: str, key: str, resource_id: str) -> None:
        self._session.add(
            ProcessedCommand(
                tenant_id=tenant_id,
                idempotency_key=key,
                resource_id=resource_id,
            )
        )

    async def commit(self) -> None:
        await self._session.commit()

    async def list_watchlists(self, tenant_id: str) -> list[Watchlist]:
        result = await self._session.execute(
            select(Watchlist)
            .where(Watchlist.tenant_id == tenant_id)
            .order_by(Watchlist.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_watchlist(self, tenant_id: str, watchlist_id: str) -> Watchlist | None:
        result = await self._session.execute(
            select(Watchlist).where(
                Watchlist.id == watchlist_id, Watchlist.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def update_watchlist(self, watchlist: Watchlist) -> None:
        await self._session.flush()

    async def delete_watchlist(self, watchlist: Watchlist) -> None:
        await self._session.delete(watchlist)
        await self._session.flush()

    async def get_alert_rule(self, tenant_id: str, rule_id: str) -> AlertRule | None:
        result = await self._session.execute(
            select(AlertRule).where(
                AlertRule.id == rule_id, AlertRule.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def soft_delete_alert_rule(self, rule: AlertRule) -> None:
        await self._session.flush()
