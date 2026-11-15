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

from cryptoscope_shared.comparators import ALLOWED_INTERVALS, validate_rule_params

from app.domain import events
from app.domain.commands import CreateAlertRule, CreateWatchlist
from app.domain.errors import ValidationError
from app.domain.models import AlertRule, Watchlist
from app.domain.repository import WriteRepository


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
        try:
            validate_rule_params(cmd.comparator, cmd.window_seconds)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        if cmd.interval not in ALLOWED_INTERVALS:
            raise ValidationError(
                f"interval must be one of: {', '.join(sorted(ALLOWED_INTERVALS))}"
            )
        if cmd.cooldown_seconds <= 0:
            raise ValidationError("cooldown_seconds must be positive")
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
            interval=cmd.interval,
            window_seconds=cmd.window_seconds,
            cooldown_seconds=cmd.cooldown_seconds,
        )
        await self._repo.add_alert_rule(rule)
        await self._repo.record_command(cmd.tenant_id, cmd.idempotency_key, rule.id)
        await self._repo.commit()

        await self._publisher.publish(
            events.alert_rule_created(
                cmd.tenant_id,
                rule.id,
                rule.symbol,
                rule.comparator,
                rule.threshold,
                interval=rule.interval,
                window_seconds=rule.window_seconds,
                cooldown_seconds=rule.cooldown_seconds,
            )
        )
        return rule.id
