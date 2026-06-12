"""Application service holding the write-side use cases.

Each handler is idempotent: it first checks the processed-commands ledger for
the client supplied key and returns the original resource id on a repeat. Only
after the database write commits do we publish the domain event, so a consumer
never sees an event for a change that did not persist.

The service depends on the WriteRepository port and an EventPublisher, so the
use cases are exercised in unit tests without any running infrastructure.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from app.domain import events
from app.domain.commands import CreateAlertRule, CreateWatchlist
from app.domain.errors import ValidationError
from app.domain.models import AlertRule, Watchlist
from app.domain.repository import WriteRepository

_VALID_COMPARATORS = {"above", "below"}


class EventPublisher(Protocol):
    async def publish(self, event: events.DomainEvent) -> None: ...


class CommandService:
    def __init__(self, repo: WriteRepository, publisher: EventPublisher) -> None:
        self._repo = repo
        self._publisher = publisher

    async def create_watchlist(self, cmd: CreateWatchlist) -> str:
        if not cmd.name.strip():
            raise ValidationError("watchlist name must not be empty")

        existing = await self._repo.resource_for_key(cmd.tenant_id, cmd.idempotency_key)
        if existing is not None:
            return existing

        watchlist = Watchlist(
            id=str(uuid.uuid4()),
            tenant_id=cmd.tenant_id,
            name=cmd.name.strip(),
            symbols=[s.upper() for s in cmd.symbols],
        )
        await self._repo.add_watchlist(watchlist)
        await self._repo.record_command(cmd.tenant_id, cmd.idempotency_key, watchlist.id)
        await self._repo.commit()

        await self._publisher.publish(
            events.watchlist_created(
                cmd.tenant_id, watchlist.id, watchlist.name, list(watchlist.symbols)
            )
        )
        return watchlist.id

    async def create_alert_rule(self, cmd: CreateAlertRule) -> str:
        if cmd.comparator not in _VALID_COMPARATORS:
            raise ValidationError("comparator must be one of: above, below")
        if not cmd.symbol.strip():
            raise ValidationError("symbol must not be empty")

        existing = await self._repo.resource_for_key(cmd.tenant_id, cmd.idempotency_key)
        if existing is not None:
            return existing

        rule = AlertRule(
            id=str(uuid.uuid4()),
            tenant_id=cmd.tenant_id,
            symbol=cmd.symbol.upper(),
            comparator=cmd.comparator,
            threshold=cmd.threshold,
        )
        await self._repo.add_alert_rule(rule)
        await self._repo.record_command(cmd.tenant_id, cmd.idempotency_key, rule.id)
        await self._repo.commit()

        await self._publisher.publish(
            events.alert_rule_created(
                cmd.tenant_id, rule.id, rule.symbol, rule.comparator, rule.threshold
            )
        )
        return rule.id
