"""Unit tests for the write-side application service."""

from __future__ import annotations

import pytest
from cryptoscope_shared.comparators import Comparator

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
    assert event.event_type == "watchlist_created"
    assert event.data["symbols"] == ["BTCUSDT", "ETHUSDT"]


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
    assert publisher.published[0].event_type == "alert_rule_created"
    assert publisher.published[0].data["symbol"] == "BTCUSDT"


# ---------------------------------------------------------------------------
# Phase 4: shared comparator vocabulary, interval, window and cooldown
# ---------------------------------------------------------------------------


def _rule_cmd(key: str, comparator: str = "above", **overrides):
    kwargs: dict = {
        "tenant_id": TENANT_ID,
        "idempotency_key": key,
        "symbol": "BTCUSDT",
        "comparator": comparator,
        "threshold": 5.0,
    }
    kwargs.update(overrides)
    return CreateAlertRule(**kwargs)


@pytest.mark.parametrize(
    "comparator", [c.value for c in Comparator]
)
async def test_create_alert_rule_accepts_every_shared_comparator(repo, publisher, comparator):
    service = CommandService(repo, publisher)
    window = 3600 if comparator.startswith("pct_change") else None
    rule_id = await service.create_alert_rule(
        _rule_cmd(f"k-{comparator}", comparator, window_seconds=window)
    )

    assert rule_id in repo.alert_rules
    assert repo.alert_rules[rule_id].comparator == comparator


async def test_create_alert_rule_defaults_interval_and_cooldown(repo, publisher):
    service = CommandService(repo, publisher)
    rule_id = await service.create_alert_rule(_rule_cmd("k-defaults"))

    rule = repo.alert_rules[rule_id]
    assert rule.interval == "1m"
    assert rule.window_seconds is None
    assert rule.cooldown_seconds == 300


@pytest.mark.parametrize("interval", ["1m", "5m", "1h"])
async def test_create_alert_rule_accepts_supported_intervals(repo, publisher, interval):
    service = CommandService(repo, publisher)
    rule_id = await service.create_alert_rule(_rule_cmd(f"k-{interval}", interval=interval))

    assert repo.alert_rules[rule_id].interval == interval


async def test_create_alert_rule_rejects_unsupported_interval(repo, publisher):
    service = CommandService(repo, publisher)
    with pytest.raises(ValidationError):
        await service.create_alert_rule(_rule_cmd("k-4h", interval="4h"))
    assert publisher.published == []


async def test_create_alert_rule_pct_change_requires_window(repo, publisher):
    service = CommandService(repo, publisher)
    with pytest.raises(ValidationError):
        await service.create_alert_rule(
            _rule_cmd("k-no-window", "pct_change_below", window_seconds=None)
        )
    assert publisher.published == []


async def test_create_alert_rule_rejects_window_on_price_comparator(repo, publisher):
    service = CommandService(repo, publisher)
    with pytest.raises(ValidationError):
        await service.create_alert_rule(_rule_cmd("k-window", "above", window_seconds=3600))
    assert publisher.published == []


async def test_create_alert_rule_rejects_non_positive_cooldown(repo, publisher):
    service = CommandService(repo, publisher)
    with pytest.raises(ValidationError):
        await service.create_alert_rule(_rule_cmd("k-cooldown", cooldown_seconds=0))
    assert publisher.published == []


async def test_create_alert_rule_event_carries_rule_params(repo, publisher):
    service = CommandService(repo, publisher)
    await service.create_alert_rule(
        _rule_cmd(
            "k-params",
            "crosses_below",
            threshold=42000.0,
            interval="5m",
            cooldown_seconds=900,
        )
    )

    event = publisher.published[0]
    assert event.data["comparator"] == "crosses_below"
    assert event.data["interval"] == "5m"
    assert event.data["cooldown_seconds"] == 900
    assert event.data["window_seconds"] is None
