from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from cryptoscope_shared.events import DomainEvent
from app.domain.models import AlertRule, AlertRuleStatus, Comparator
from app.infra.consumer import AlertEngine


@pytest.mark.asyncio
async def test_evaluate_gt_rule_triggers() -> None:
    rule = make_rule(comparator=Comparator.GT, threshold=100.0)
    engine = make_engine()
    assert engine._evaluate_rule(rule, 101.0) is True


@pytest.mark.asyncio
async def test_evaluate_gt_rule_does_not_trigger() -> None:
    rule = make_rule(comparator=Comparator.GT, threshold=100.0)
    engine = make_engine()
    assert engine._evaluate_rule(rule, 99.0) is False


@pytest.mark.asyncio
async def test_evaluate_gte_rule_triggers_on_equal() -> None:
    rule = make_rule(comparator=Comparator.GTE, threshold=100.0)
    engine = make_engine()
    assert engine._evaluate_rule(rule, 100.0) is True


@pytest.mark.asyncio
async def test_evaluate_lt_rule_triggers() -> None:
    rule = make_rule(comparator=Comparator.LT, threshold=100.0)
    engine = make_engine()
    assert engine._evaluate_rule(rule, 50.0) is True


@pytest.mark.asyncio
async def test_evaluate_eq_rule_triggers() -> None:
    rule = make_rule(comparator=Comparator.EQ, threshold=100.0)
    engine = make_engine()
    assert engine._evaluate_rule(rule, 100.00005) is True


@pytest.mark.asyncio
async def test_evaluate_eq_rule_does_not_trigger() -> None:
    rule = make_rule(comparator=Comparator.EQ, threshold=100.0)
    engine = make_engine()
    assert engine._evaluate_rule(rule, 101.0) is False


@pytest.mark.asyncio
async def test_fire_trigger_publishes_and_persists() -> None:
    producer = FakeProducer()
    rules = [
        {
            "id": "rule-1",
            "tenant_id": "tenant-1",
            "symbol": "BTCUSDT",
            "comparator": "gt",
            "threshold": 50000.0,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    ]
    engine = AlertEngine(
        consumer=FakeConsumer([]),
        producer=producer,
        alerts_topic="alerts.triggers",
        session_factory=FakeSessionFactory(rules),
        logger=FakeLogger(),
    )

    rule = AlertRule(
        id="rule-1",
        tenant_id="tenant-1",
        symbol="BTCUSDT",
        comparator=Comparator.GT,
        threshold=50000.0,
        status=AlertRuleStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    await engine._fire_trigger(rule, 51000.0, "tenant-1")

    assert len(producer.published) == 1
    topic, key, data = producer.published[0]
    assert topic == "alerts.triggers"
    assert key == "BTCUSDT"
    assert data["threshold"] == 50000.0
    assert data["current_value"] == 51000.0


def make_rule(
    comparator: Comparator = Comparator.GT,
    threshold: float = 100.0,
) -> AlertRule:
    now = datetime.now(timezone.utc)
    return AlertRule(
        id="test-rule",
        tenant_id="tenant-1",
        symbol="BTCUSDT",
        comparator=comparator,
        threshold=threshold,
        status=AlertRuleStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def make_engine() -> AlertEngine:
    return AlertEngine(
        consumer=FakeConsumer([]),
        producer=FakeProducer(),
        alerts_topic="alerts.triggers",
        session_factory=FakeSessionFactory([]),
        logger=FakeLogger(),
    )


class FakeConsumer:
    def __init__(self, messages: list[tuple[str, dict[str, Any]]]) -> None:
        self._messages = messages

    async def start(self) -> None:
        pass

    async def messages(self) -> Any:
        for msg in self._messages:
            yield msg

    async def stop(self) -> None:
        pass


class FakeProducer:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, dict[str, Any]]] = []

    async def start(self) -> None:
        pass

    async def publish(self, topic: str, key: str, value: dict[str, Any]) -> None:
        self.published.append((topic, key, value))

    async def stop(self) -> None:
        pass


class FakeSessionFactory:
    def __init__(self, rules: list[dict[str, Any]]) -> None:
        self._rules = rules

    async def __aenter__(self) -> FakeSession:
        return FakeSession(self._rules)

    async def __aexit__(self, *args: Any) -> None:
        pass

    def __call__(self) -> FakeSession:
        return FakeSession(self._rules)


class FakeSession:
    def __init__(self, rules: list[dict[str, Any]]) -> None:
        self._rules = rules
        self._added: list[Any] = []

    async def execute(self, query: Any) -> Any:
        return FakeResult(self._rules)

    async def commit(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def add(self, obj: Any) -> None:
        self._added.append(obj)


class FakeResult:
    def __init__(self, rules: list[dict[str, Any]]) -> None:
        self._rules = rules

    def scalars(self) -> FakeResult:
        return self

    def all(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(**r) for r in self._rules]

    def scalar_one_or_none(self) -> SimpleNamespace | None:
        if not self._rules:
            return None
        return SimpleNamespace(**self._rules[0])


class FakeLogger:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def info(self, *args: Any, **kwargs: Any) -> None:
        self.messages.append({"level": "info", "args": args, "kwargs": kwargs})

    def debug(self, *args: Any, **kwargs: Any) -> None:
        self.messages.append({"level": "debug", "args": args, "kwargs": kwargs})

    def warning(self, *args: Any, **kwargs: Any) -> None:
        self.messages.append({"level": "warning", "args": args, "kwargs": kwargs})

    def error(self, *args: Any, **kwargs: Any) -> None:
        self.messages.append({"level": "error", "args": args, "kwargs": kwargs})

    def exception(self, *args: Any, **kwargs: Any) -> None:
        self.messages.append({"level": "exception", "args": args, "kwargs": kwargs})


@pytest.mark.asyncio
async def test_process_recognizes_watchlist_created_event() -> None:
    """A watchlist_created event produced by command-service using the shared
    schema should be accepted (not dropped as unknown)."""
    producer = FakeProducer()
    logger = FakeLogger()
    engine = AlertEngine(
        consumer=FakeConsumer([]),
        producer=producer,
        alerts_topic="alerts.triggers",
        session_factory=FakeSessionFactory([]),
        logger=logger,
    )

    payload = DomainEvent(
        event_type="watchlist_created",
        aggregate_id="wl-1",
        tenant_id="tenant-1",
        data={"id": "wl-1", "name": "Majors", "symbols": ["BTCUSDT"]},
    ).to_message()

    await engine._process(payload)

    assert any(
        m["level"] == "info" and "watchlist_created" in str(m["kwargs"])
        for m in logger.messages
    ), "expected info log for watchlist_created"


@pytest.mark.asyncio
async def test_process_recognizes_alert_rule_created_event() -> None:
    """An alert_rule_created event should be recognized and logged."""
    producer = FakeProducer()
    logger = FakeLogger()
    engine = AlertEngine(
        consumer=FakeConsumer([]),
        producer=producer,
        alerts_topic="alerts.triggers",
        session_factory=FakeSessionFactory([]),
        logger=logger,
    )

    payload = DomainEvent(
        event_type="alert_rule_created",
        aggregate_id="rule-1",
        tenant_id="tenant-1",
        data={"id": "rule-1", "symbol": "BTCUSDT", "comparator": "gt", "threshold": 50000.0},
    ).to_message()

    await engine._process(payload)

    assert any(
        m["level"] == "info" and "alert_rule_created" in str(m["kwargs"])
        for m in logger.messages
    ), "expected info log for alert_rule_created"


@pytest.mark.asyncio
async def test_process_ignores_unknown_event_type() -> None:
    """Unknown event types should be logged at debug level and ignored."""
    producer = FakeProducer()
    logger = FakeLogger()
    engine = AlertEngine(
        consumer=FakeConsumer([]),
        producer=producer,
        alerts_topic="alerts.triggers",
        session_factory=FakeSessionFactory([]),
        logger=logger,
    )

    payload = DomainEvent(
        event_type="unknown.event",
        aggregate_id="",
        tenant_id="tenant-1",
        data={},
    ).to_message()

    await engine._process(payload)

    assert any(
        m["level"] == "debug" and "unknown" in str(m["kwargs"]).lower()
        for m in logger.messages
    ), "expected debug log for unknown event type"


@pytest.mark.asyncio
async def test_candle_updated_triggers_evaluation_with_matching_rules() -> None:
    """A candle_updated event with a matching active rule should fire a trigger."""
    producer = FakeProducer()
    rules = [
        {
            "id": "rule-1",
            "tenant_id": "tenant-1",
            "symbol": "BTCUSDT",
            "comparator": "gt",
            "threshold": 50000.0,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    ]
    engine = AlertEngine(
        consumer=FakeConsumer([]),
        producer=producer,
        alerts_topic="alerts.triggers",
        session_factory=FakeSessionFactory(rules),
        logger=FakeLogger(),
    )

    payload = DomainEvent(
        event_type="candle_updated",
        aggregate_id="BTCUSDT:1m:1710000000000",
        tenant_id="tenant-1",
        data={
            "symbol": "BTCUSDT",
            "interval": "1m",
            "open": 49000.0,
            "high": 51000.0,
            "low": 49000.0,
            "close": 51000.0,
            "volume": 100.0,
            "timestamp": 1710000000000,
        },
    ).to_message()

    await engine._process(payload)

    assert len(producer.published) == 1
    topic, key, data = producer.published[0]
    assert topic == "alerts.triggers"
    assert key == "BTCUSDT"
    assert data["threshold"] == 50000.0
    assert data["current_value"] == 51000.0


@pytest.mark.asyncio
async def test_candle_updated_no_fire_when_rule_does_not_match() -> None:
    """A candle_updated event that does not satisfy the threshold should not fire."""
    producer = FakeProducer()
    rules = [
        {
            "id": "rule-1",
            "tenant_id": "tenant-1",
            "symbol": "BTCUSDT",
            "comparator": "gt",
            "threshold": 60000.0,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    ]
    engine = AlertEngine(
        consumer=FakeConsumer([]),
        producer=producer,
        alerts_topic="alerts.triggers",
        session_factory=FakeSessionFactory(rules),
        logger=FakeLogger(),
    )

    payload = DomainEvent(
        event_type="candle_updated",
        aggregate_id="BTCUSDT:1m:1710000000000",
        tenant_id="tenant-1",
        data={
            "symbol": "BTCUSDT",
            "interval": "1m",
            "open": 49000.0,
            "high": 51000.0,
            "low": 49000.0,
            "close": 51000.0,
            "volume": 100.0,
            "timestamp": 1710000000000,
        },
    ).to_message()

    await engine._process(payload)

    assert len(producer.published) == 0, "should not fire when threshold not met"
