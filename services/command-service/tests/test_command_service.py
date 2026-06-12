"""Unit tests for the write-side application service."""

from __future__ import annotations

import pytest

from app.domain.commands import CreateAlertRule, CreateWatchlist
from app.domain.errors import ValidationError
from app.domain.service import CommandService
from tests.conftest import TENANT_ID


async def test_create_watchlist_persists_and_emits_event(repo, publisher):
    service = CommandService(repo, publisher)
    watchlist_id = await service.create_watchlist(
        CreateWatchlist(
            tenant_id=TENANT_ID,
            idempotency_key="key-1",
            name="Majors",
            symbols=["btcusdt", "ethusdt"],
        )
    )

    assert watchlist_id in repo.watchlists
    assert repo.watchlists[watchlist_id].symbols == ["BTCUSDT", "ETHUSDT"]
    assert len(publisher.published) == 1
    event = publisher.published[0]
    assert event.name == "watchlist.created"
    assert event.payload["symbols"] == ["BTCUSDT", "ETHUSDT"]


async def test_create_watchlist_rejects_blank_name(repo, publisher):
    service = CommandService(repo, publisher)
    with pytest.raises(ValidationError):
        await service.create_watchlist(
            CreateWatchlist(
                tenant_id=TENANT_ID,
                idempotency_key="key-blank",
                name="   ",
                symbols=[],
            )
        )
    assert publisher.published == []


async def test_create_watchlist_is_idempotent(repo, publisher):
    cmd = CreateWatchlist(
        tenant_id=TENANT_ID,
        idempotency_key="same-key",
        name="Majors",
        symbols=["BTCUSDT"],
    )
    first = await CommandService(repo, publisher).create_watchlist(cmd)
    second = await CommandService(repo, publisher).create_watchlist(cmd)

    assert first == second
    assert len(repo.watchlists) == 1
    # Only the first call should have emitted an event.
    assert len(publisher.published) == 1


async def test_create_alert_rule_rejects_bad_comparator(repo, publisher):
    service = CommandService(repo, publisher)
    with pytest.raises(ValidationError):
        await service.create_alert_rule(
            CreateAlertRule(
                tenant_id=TENANT_ID,
                idempotency_key="k",
                symbol="BTCUSDT",
                comparator="sideways",
                threshold=1.0,
            )
        )
    assert publisher.published == []


async def test_create_alert_rule_persists_and_emits_event(repo, publisher):
    service = CommandService(repo, publisher)
    rule_id = await service.create_alert_rule(
        CreateAlertRule(
            tenant_id=TENANT_ID,
            idempotency_key="rule-1",
            symbol="btcusdt",
            comparator="above",
            threshold=70000.0,
        )
    )

    assert rule_id in repo.alert_rules
    assert repo.alert_rules[rule_id].symbol == "BTCUSDT"
    assert publisher.published[0].name == "alert_rule.created"
    assert publisher.published[0].payload["symbol"] == "BTCUSDT"
