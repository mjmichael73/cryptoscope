from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from unittest.mock import MagicMock

from cryptoscope_shared.events import DomainEvent
from app.domain.models import AlertRule, AlertRuleStatus, Comparator
from app.infra.consumer import AlertEngine
from app.infra.notify import NotificationChannel, NotificationDispatcher, TriggerPayload


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
    def __init__(
        self,
        rules: list[dict[str, Any]],
        filter_fn: Any | None = None,
    ) -> None:
        self._rules = rules
        self._filter_fn = filter_fn

    async def __aenter__(self) -> FakeSession:
        return FakeSession(self._rules, self._filter_fn)

    async def __aexit__(self, *args: Any) -> None:
        pass

    def __call__(self) -> FakeSession:
        return FakeSession(self._rules, self._filter_fn)


class FakeSession:
    def __init__(
        self,
        rules: list[dict[str, Any]],
        filter_fn: Any | None = None,
    ) -> None:
        self._rules = rules
        self._filter_fn = filter_fn
        self._added: list[Any] = []

    async def execute(self, query: Any) -> Any:
        rules = self._filter_fn(self._rules) if self._filter_fn else self._rules
        return FakeResult(rules)

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


# ---------------------------------------------------------------------------
# Integration tests: dispatcher called during full engine flow
# ---------------------------------------------------------------------------


def _make_candle_payload(
    symbol: str = "BTCUSDT",
    close: float = 51000.0,
    tenant_id: str = "tenant-1",
) -> dict[str, Any]:
    return DomainEvent(
        event_type="candle_updated",
        aggregate_id=f"{symbol}:1m:1710000000000",
        tenant_id=tenant_id,
        data={
            "symbol": symbol,
            "interval": "1m",
            "open": close - 1000.0,
            "high": close + 500.0,
            "low": close - 1500.0,
            "close": close,
            "volume": 100.0,
            "timestamp": 1710000000000,
        },
    ).to_message()


class _RecordingChannel(NotificationChannel):
    """Channel that records every TriggerPayload it receives."""

    def __init__(self) -> None:
        self.received: list[TriggerPayload] = []
        self._should_fail = False

    def send(self, trigger: TriggerPayload) -> bool:
        self.received.append(trigger)
        return not self._should_fail

    def set_fail(self, fail: bool) -> None:
        self._should_fail = fail


def _active_only(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rules if r.get("status") == "active"]


def _build_engine_with_dispatcher(
    rules: list[dict[str, Any]],
    dispatcher: NotificationDispatcher,
    filter_rules: bool = True,
) -> AlertEngine:
    filter_fn = _active_only if filter_rules else None
    return AlertEngine(
        consumer=FakeConsumer([]),
        producer=FakeProducer(),
        alerts_topic="alerts.triggers",
        session_factory=FakeSessionFactory(rules, filter_fn=filter_fn),
        logger=FakeLogger(),
        dispatcher=dispatcher,
    )


@pytest.mark.asyncio
async def test_dispatcher_called_when_candle_triggers_alert() -> None:
    """When a candle_updated event matches a rule, the dispatcher receives the
    correct TriggerPayload with all fields populated."""
    ch = _RecordingChannel()
    dispatcher = NotificationDispatcher([ch])
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
    engine = _build_engine_with_dispatcher(rules, dispatcher)

    await engine._process(_make_candle_payload(close=51000.0))

    assert len(ch.received) == 1
    payload = ch.received[0]
    assert payload.symbol == "BTCUSDT"
    assert payload.tenant_id == "tenant-1"
    assert payload.rule_id == "rule-1"
    assert payload.comparator == "gt"
    assert payload.threshold == 50000.0
    assert payload.current_value == 51000.0
    assert payload.trigger_id  # non-empty UUID
    assert payload.triggered_at  # non-empty ISO timestamp


@pytest.mark.asyncio
async def test_dispatcher_not_called_when_no_match() -> None:
    """If the candle close does not satisfy the threshold the dispatcher
    must not be called."""
    ch = _RecordingChannel()
    dispatcher = NotificationDispatcher([ch])
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
    engine = _build_engine_with_dispatcher(rules, dispatcher)

    await engine._process(_make_candle_payload(close=51000.0))

    assert len(ch.received) == 0, "dispatcher should not be called for non-matching rule"


@pytest.mark.asyncio
async def test_dispatcher_called_for_multiple_matching_rules() -> None:
    """If multiple active rules match, the dispatcher is called once per rule."""
    ch = _RecordingChannel()
    dispatcher = NotificationDispatcher([ch])
    now = datetime.now(timezone.utc)
    rules = [
        {
            "id": "rule-gt",
            "tenant_id": "tenant-1",
            "symbol": "BTCUSDT",
            "comparator": "gt",
            "threshold": 50000.0,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "rule-gte",
            "tenant_id": "tenant-1",
            "symbol": "BTCUSDT",
            "comparator": "gte",
            "threshold": 51000.0,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "rule-lt",
            "tenant_id": "tenant-1",
            "symbol": "BTCUSDT",
            "comparator": "lt",
            "threshold": 52000.0,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
    ]
    engine = _build_engine_with_dispatcher(rules, dispatcher)

    await engine._process(_make_candle_payload(close=51000.0))

    # gt(50000) ✓, gte(51000) ✓, lt(52000) ✓  → 3 triggers
    assert len(ch.received) == 3
    rule_ids = {p.rule_id for p in ch.received}
    assert rule_ids == {"rule-gt", "rule-gte", "rule-lt"}


@pytest.mark.asyncio
async def test_dispatcher_called_per_symbol_independently() -> None:
    """Rules are scoped by (tenant_id, symbol). Only matching symbols fire."""
    ch = _RecordingChannel()
    dispatcher = NotificationDispatcher([ch])
    now = datetime.now(timezone.utc)
    rules = [
        {
            "id": "rule-btc",
            "tenant_id": "tenant-1",
            "symbol": "BTCUSDT",
            "comparator": "gt",
            "threshold": 50000.0,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "rule-eth",
            "tenant_id": "tenant-1",
            "symbol": "ETHUSDT",
            "comparator": "gt",
            "threshold": 2000.0,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
    ]
    # Process BTCUSDT event — only the BTCUSDT rule should fire.
    # Use a session factory that only returns the BTCUSDT rule to prove
    # symbol isolation at the query level.
    btc_rules = [r for r in rules if r["symbol"] == "BTCUSDT"]
    btc_factory = FakeSessionFactory(btc_rules, filter_fn=_active_only)
    engine_btc = AlertEngine(
        consumer=FakeConsumer([]),
        producer=FakeProducer(),
        alerts_topic="alerts.triggers",
        session_factory=btc_factory,
        logger=FakeLogger(),
        dispatcher=dispatcher,
    )
    await engine_btc._process(_make_candle_payload(symbol="BTCUSDT", close=51000.0))
    assert len(ch.received) == 1
    assert ch.received[0].rule_id == "rule-btc"
    assert ch.received[0].symbol == "BTCUSDT"

    # Process ETHUSDT event — only the ETHUSDT rule should fire.
    eth_rules = [r for r in rules if r["symbol"] == "ETHUSDT"]
    eth_factory = FakeSessionFactory(eth_rules, filter_fn=_active_only)
    engine_eth = AlertEngine(
        consumer=FakeConsumer([]),
        producer=FakeProducer(),
        alerts_topic="alerts.triggers",
        session_factory=eth_factory,
        logger=FakeLogger(),
        dispatcher=dispatcher,
    )
    await engine_eth._process(_make_candle_payload(symbol="ETHUSDT", close=2100.0))
    assert len(ch.received) == 2
    assert ch.received[1].rule_id == "rule-eth"
    assert ch.received[1].symbol == "ETHUSDT"


@pytest.mark.asyncio
async def test_dispatcher_failure_does_not_break_engine() -> None:
    """If the dispatcher raises, the engine should still persist the trigger
    and publish to Kafka — notification failure must not crash the pipeline."""
    ch = _RecordingChannel()
    ch.set_fail(True)
    dispatcher = NotificationDispatcher([ch])
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
        dispatcher=dispatcher,
    )

    # Should not raise
    await engine._process(_make_candle_payload(close=51000.0))

    # Trigger persisted + published even though notification failed
    assert len(producer.published) == 1
    assert producer.published[0][0] == "alerts.triggers"
    # Channel received it (returned False)
    assert len(ch.received) == 1


@pytest.mark.asyncio
async def test_dispatcher_exception_caught_by_engine() -> None:
    """If the dispatcher throws an exception (not just returns False), the
    engine must catch it and continue."""
    broken = MagicMock(spec=NotificationChannel)
    broken.send.side_effect = RuntimeError("channel exploded")
    dispatcher = NotificationDispatcher([broken])
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
        session_factory=FakeSessionFactory(rules, filter_fn=_active_only),
        logger=FakeLogger(),
        dispatcher=dispatcher,
    )

    # Should not raise despite RuntimeError from dispatcher
    await engine._process(_make_candle_payload(close=51000.0))

    # Trigger still persisted + published
    assert len(producer.published) == 1


@pytest.mark.asyncio
async def test_dispatcher_payload_has_unique_trigger_id() -> None:
    """Each trigger dispatched must carry a unique trigger_id."""
    ch = _RecordingChannel()
    dispatcher = NotificationDispatcher([ch])
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
    engine = _build_engine_with_dispatcher(rules, dispatcher)

    await engine._process(_make_candle_payload(close=51000.0))
    await engine._process(_make_candle_payload(close=52000.0))

    assert len(ch.received) == 2
    ids = {p.trigger_id for p in ch.received}
    assert len(ids) == 2, "each trigger must have a unique ID"


@pytest.mark.asyncio
async def test_non_candle_event_does_not_dispatch() -> None:
    """Non-candle events (watchlist_created, etc.) must never reach the
    notification dispatcher."""
    ch = _RecordingChannel()
    dispatcher = NotificationDispatcher([ch])
    engine = _build_engine_with_dispatcher([], dispatcher)

    payload = DomainEvent(
        event_type="watchlist_created",
        aggregate_id="wl-1",
        tenant_id="tenant-1",
        data={},
    ).to_message()
    await engine._process(payload)

    assert len(ch.received) == 0


@pytest.mark.asyncio
async def test_disabled_rule_does_not_dispatch() -> None:
    """A rule with status=paused must not trigger notifications."""
    ch = _RecordingChannel()
    dispatcher = NotificationDispatcher([ch])
    rules = [
        {
            "id": "rule-1",
            "tenant_id": "tenant-1",
            "symbol": "BTCUSDT",
            "comparator": "gt",
            "threshold": 50000.0,
            "status": "paused",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    ]
    engine = _build_engine_with_dispatcher(rules, dispatcher)

    await engine._process(_make_candle_payload(close=51000.0))

    assert len(ch.received) == 0, "paused rule should not fire"
