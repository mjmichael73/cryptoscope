from __future__ import annotations

from datetime import UTC, datetime

from app.domain.models import (
    AlertRule,
    AlertRuleStatus,
    AlertTrigger,
    CandleUpdate,
    Comparator,
    DomainEvent,
)


def test_alert_rule_defaults() -> None:
    now = datetime.now(UTC)
    rule = AlertRule(
        id="rule-1",
        tenant_id="tenant-1",
        symbol="BTCUSDT",
        comparator=Comparator.ABOVE,
        threshold=50000.0,
        status=AlertRuleStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    assert rule.id == "rule-1"
    assert rule.comparator == Comparator.ABOVE
    assert rule.interval == "1m"
    assert rule.window_seconds is None
    assert rule.cooldown_seconds == 300


def test_alert_rule_status_enum() -> None:
    assert AlertRuleStatus.ACTIVE.value == "active"
    assert AlertRuleStatus.PAUSED.value == "paused"
    assert AlertRuleStatus.TRIGGERED.value == "triggered"


def test_comparator_enum_is_the_shared_vocabulary() -> None:
    assert {c.value for c in Comparator} == {
        "above",
        "below",
        "crosses_above",
        "crosses_below",
        "pct_change_above",
        "pct_change_below",
        "rsi_above",
        "rsi_below",
    }


def test_alert_trigger_defaults() -> None:
    now = datetime.now(UTC)
    trigger = AlertTrigger(
        id="trigger-1",
        tenant_id="tenant-1",
        rule_id="rule-1",
        symbol="BTCUSDT",
        comparator=Comparator.ABOVE,
        threshold=50000.0,
        current_value=51000.0,
        triggered_at=now,
        acknowledged=False,
    )
    assert trigger.acknowledged is False
    assert trigger.current_value == 51000.0
    assert trigger.interval == "1m"
    assert trigger.window_seconds is None


def test_domain_event() -> None:
    event = DomainEvent(
        event_type="tick.processed",
        aggregate_id="BTCUSDT",
        tenant_id="tenant-1",
        data={"price": 50000.0},
        timestamp=1700000000000,
    )
    assert event.event_type == "tick.processed"
    assert event.data["price"] == 50000.0


def test_candle_update() -> None:
    update = CandleUpdate(
        symbol="BTCUSDT",
        interval="1m",
        open=49000.0,
        high=51000.0,
        low=48000.0,
        close=50500.0,
        volume=100.5,
        timestamp=1700000000000,
    )
    assert update.symbol == "BTCUSDT"
    assert update.close == 50500.0


def test_alert_rule_paused_status() -> None:
    now = datetime.now(UTC)
    rule = AlertRule(
        id="rule-2",
        tenant_id="tenant-1",
        symbol="ETHUSDT",
        comparator=Comparator.BELOW,
        threshold=2000.0,
        status=AlertRuleStatus.PAUSED,
        created_at=now,
        updated_at=now,
    )
    assert rule.status == AlertRuleStatus.PAUSED
    assert rule.threshold == 2000.0
