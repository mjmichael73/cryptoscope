"""Unit tests for the write-side application service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from cryptoscope_shared.comparators import Comparator

from app.domain.commands import CreateAlertRule, CreateWatchlist, UpdateWatchlist
from app.domain.errors import NotFoundError, ValidationError
from app.domain.models import Watchlist
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


# ---------------------------------------------------------------------------
# Phase 5: watchlist CRUD
# ---------------------------------------------------------------------------


def _wl(name: str, symbols: list[str], tenant: str = TENANT_ID) -> Watchlist:
    return Watchlist(id=str(uuid4()), tenant_id=tenant, name=name, symbols=symbols)


async def test_list_watchlists_returns_newest_first(repo, publisher):
    service = CommandService(repo, publisher)
    older = _wl("Old", ["BTCUSDT"])
    older.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    newer = _wl("New", ["ETHUSDT"])
    newer.created_at = datetime(2026, 6, 1, tzinfo=UTC)
    repo.watchlists[older.id] = older
    repo.watchlists[newer.id] = newer

    result = await service.list_watchlists(TENANT_ID)

    assert [w.name for w in result] == ["New", "Old"]


async def test_list_watchlists_scopes_to_tenant(repo, publisher):
    service = CommandService(repo, publisher)
    mine = _wl("Mine", ["BTCUSDT"])
    theirs = _wl("Theirs", ["ETHUSDT"], tenant="22222222-2222-2222-2222-222222222222")
    repo.watchlists[mine.id] = mine
    repo.watchlists[theirs.id] = theirs

    result = await service.list_watchlists(TENANT_ID)

    assert [w.name for w in result] == ["Mine"]


async def test_get_watchlist_returns_it(repo, publisher):
    service = CommandService(repo, publisher)
    wl = _wl("Mine", ["BTCUSDT"])
    repo.watchlists[wl.id] = wl

    assert await service.get_watchlist(TENANT_ID, wl.id) is wl


async def test_get_watchlist_unknown_id_raises_not_found(repo, publisher):
    service = CommandService(repo, publisher)
    with pytest.raises(NotFoundError):
        await service.get_watchlist(TENANT_ID, "missing-id")


async def test_get_watchlist_other_tenant_raises_not_found(repo, publisher):
    service = CommandService(repo, publisher)
    theirs = _wl("Theirs", ["BTCUSDT"], tenant="22222222-2222-2222-2222-222222222222")
    repo.watchlists[theirs.id] = theirs

    with pytest.raises(NotFoundError):
        await service.get_watchlist(TENANT_ID, theirs.id)


async def test_update_watchlist_renames_and_replaces_symbols(repo, publisher):
    service = CommandService(repo, publisher)
    wl = _wl("Old Name", ["BTCUSDT"])
    repo.watchlists[wl.id] = wl

    updated = await service.update_watchlist(
        UpdateWatchlist(
            tenant_id=TENANT_ID, watchlist_id=wl.id, name="New Name", symbols=["ethusdt"]
        )
    )

    assert updated.name == "New Name"
    assert updated.symbols == ["ETHUSDT"]
    assert repo.watchlists[wl.id].name == "New Name"
    assert publisher.published[0].event_type == "watchlist_updated"
    assert publisher.published[0].data["symbols"] == ["ETHUSDT"]


async def test_update_watchlist_rejects_empty_name(repo, publisher):
    service = CommandService(repo, publisher)
    wl = _wl("Mine", ["BTCUSDT"])
    repo.watchlists[wl.id] = wl

    with pytest.raises(ValidationError):
        await service.update_watchlist(
            UpdateWatchlist(tenant_id=TENANT_ID, watchlist_id=wl.id, name="  ", symbols=[])
        )
    assert publisher.published == []


async def test_update_watchlist_unknown_id_raises(repo, publisher):
    service = CommandService(repo, publisher)
    with pytest.raises(NotFoundError):
        await service.update_watchlist(
            UpdateWatchlist(
                tenant_id=TENANT_ID, watchlist_id="missing", name="X", symbols=[]
            )
        )


async def test_delete_watchlist_removes_and_emits_event(repo, publisher):
    service = CommandService(repo, publisher)
    wl = _wl("Mine", ["BTCUSDT"])
    repo.watchlists[wl.id] = wl

    await service.delete_watchlist(TENANT_ID, wl.id)

    assert wl.id not in repo.watchlists
    assert publisher.published[0].event_type == "watchlist_deleted"
    assert publisher.published[0].aggregate_id == wl.id


async def test_delete_watchlist_unknown_id_raises(repo, publisher):
    service = CommandService(repo, publisher)
    with pytest.raises(NotFoundError):
        await service.delete_watchlist(TENANT_ID, "missing")


async def test_replayed_create_still_returns_original_id(repo, publisher):
    service = CommandService(repo, publisher)
    first = await service.create_watchlist(
        CreateWatchlist(
            tenant_id=TENANT_ID, idempotency_key="same-key", name="WL", symbols=["BTCUSDT"]
        )
    )
    second = await service.create_watchlist(
        CreateWatchlist(
            tenant_id=TENANT_ID, idempotency_key="same-key", name="WL", symbols=["BTCUSDT"]
        )
    )

    assert first == second
    assert len(publisher.published) == 1


# ---------------------------------------------------------------------------
# Phase 5: alert rule delete
# ---------------------------------------------------------------------------


async def test_delete_alert_rule_soft_deletes_and_emits(repo, publisher):
    service = CommandService(repo, publisher)
    rule_id = await service.create_alert_rule(
        CreateAlertRule(
            tenant_id=TENANT_ID,
            idempotency_key="rule-del",
            symbol="BTCUSDT",
            comparator="above",
            threshold=5.0,
        )
    )

    await service.delete_alert_rule(TENANT_ID, rule_id)

    assert repo.alert_rules[rule_id].status == "deleted"
    assert publisher.published[-1].event_type == "alert_rule_deleted"
    assert publisher.published[-1].aggregate_id == rule_id


async def test_delete_alert_rule_unknown_id_raises(repo, publisher):
    service = CommandService(repo, publisher)
    with pytest.raises(NotFoundError):
        await service.delete_alert_rule(TENANT_ID, "missing")


async def test_delete_alert_rule_other_tenant_raises(repo, publisher):
    service = CommandService(repo, publisher)
    other_tenant = "22222222-2222-2222-2222-222222222222"
    rule_id = await service.create_alert_rule(
        CreateAlertRule(
            tenant_id=other_tenant,
            idempotency_key="rule-other",
            symbol="BTCUSDT",
            comparator="above",
            threshold=5.0,
        )
    )

    with pytest.raises(NotFoundError):
        await service.delete_alert_rule(TENANT_ID, rule_id)
