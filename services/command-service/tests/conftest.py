"""Shared fixtures.

Unit tests run the write-side use cases against an in-memory fake repository so
they need no database at all. The SQLAlchemy adapter is covered separately by
the integration tests that run against a real Postgres.
"""

from __future__ import annotations

import pytest

from app.domain import events
from app.domain.models import AlertRule, Watchlist

TENANT_ID = "11111111-1111-1111-1111-111111111111"


class FakePublisher:
    def __init__(self) -> None:
        self.published: list[events.DomainEvent] = []

    async def publish(self, event: events.DomainEvent) -> None:
        self.published.append(event)


class FakeRepository:
    """In-memory stand-in for the write repository.

    It mirrors the real adapter closely: writes accumulate in pending lists and
    are moved into the stored maps on commit, and the idempotency ledger is a
    dict keyed by tenant and key.
    """

    def __init__(self) -> None:
        self.watchlists: dict[str, Watchlist] = {}
        self.alert_rules: dict[str, AlertRule] = {}
        self._ledger: dict[tuple[str, str], str] = {}
        self._pending: list[object] = []
        self._pending_ledger: list[tuple[str, str, str]] = []

    async def resource_for_key(self, tenant_id: str, key: str) -> str | None:
        return self._ledger.get((tenant_id, key))

    async def add_watchlist(self, watchlist: Watchlist) -> None:
        self._pending.append(watchlist)

    async def add_alert_rule(self, rule: AlertRule) -> None:
        self._pending.append(rule)

    async def record_command(self, tenant_id: str, key: str, resource_id: str) -> None:
        self._pending_ledger.append((tenant_id, key, resource_id))

    async def commit(self) -> None:
        for item in self._pending:
            if isinstance(item, Watchlist):
                self.watchlists[item.id] = item
            elif isinstance(item, AlertRule):
                self.alert_rules[item.id] = item
        for tenant_id, key, resource_id in self._pending_ledger:
            self._ledger[(tenant_id, key)] = resource_id
        self._pending.clear()
        self._pending_ledger.clear()


@pytest.fixture
def repo() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def publisher() -> FakePublisher:
    return FakePublisher()
