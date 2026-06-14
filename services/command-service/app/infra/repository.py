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
