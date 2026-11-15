from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, Self
from unittest.mock import MagicMock

import pytest
from cryptoscope_shared.comparators import Comparator
from cryptoscope_shared.events import DomainEvent

from app.domain.models import AlertRule, AlertRuleStatus
from app.infra.consumer import AlertEngine
from app.infra.history import PriceHistory
from app.infra.notify import NotificationChannel, NotificationDispatcher, TriggerPayload

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


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


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]], scalar_value: Any = None) -> None:
        self._rows = rows
        self._scalar_value = scalar_value

    def scalars(self) -> FakeResult:
        return self

    def all(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(**r) for r in self._rows]

    def scalar_one_or_none(self) -> SimpleNamespace | None:
        if not self._rows:
            return None
        return SimpleNamespace(**self._rows[0])

    def scalar(self) -> Any:
        return self._scalar_value


class FakeSession:
    """Dispatches by queried table: rule selects vs trigger-timestamp selects."""

    def __init__(
        self,
        rules: list[dict[str, Any]],
        last_triggered_at: datetime | None = None,
    ) -> None:
        self._rules = rules
        self._last_triggered_at = last_triggered_at
        self._added: list[Any] = []

    async def execute(self, query: Any) -> FakeResult:
        if "alert_triggers" in str(query):
            return FakeResult([], scalar_value=self._last_triggered_at)
        return FakeResult(self._rules)

    async def commit(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    def add(self, obj: Any) -> None:
        self._added.append(obj)


class FakeSessionFactory:
    def __init__(
        self,
        rules: list[dict[str, Any]],
        last_triggered_at: datetime | None = None,
        filter_fn: Any | None = None,
    ) -> None:
        self._rules = rules
        self._last_triggered_at = last_triggered_at
        self._filter_fn = filter_fn

    def _session(self) -> FakeSession:
        rules = self._filter_fn(self._rules) if self._filter_fn else self._rules
        return FakeSession(rules, self._last_triggered_at)

    async def __aenter__(self) -> FakeSession:
        return self._session()

    async def __aexit__(self, *args: object) -> None:
        pass

    def __call__(self) -> FakeSession:
        return self._session()


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


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def make_rule(
    comparator: Comparator = Comparator.ABOVE,
    threshold: float = 100.0,
    interval: str = "1m",
    window_seconds: int | None = None,
    cooldown_seconds: int = 300,
) -> AlertRule:
    now = datetime.now(UTC)
    return AlertRule(
        id="test-rule",
        tenant_id="tenant-1",
        symbol="BTCUSDT",
        comparator=comparator,
        threshold=threshold,
        status=AlertRuleStatus.ACTIVE,
        interval=interval,
        window_seconds=window_seconds,
        cooldown_seconds=cooldown_seconds,
        created_at=now,
        updated_at=now,
    )


def make_engine(
    rules: list[dict[str, Any]] | None = None,
    producer: FakeProducer | None = None,
    last_triggered_at: datetime | None = None,
    filter_fn: Any | None = None,
    logger: FakeLogger | None = None,
) -> AlertEngine:
    return AlertEngine(
        consumer=FakeConsumer([]),
        producer=producer or FakeProducer(),
        alerts_topic="alerts.triggers",
        session_factory=FakeSessionFactory(
            rules or [], last_triggered_at=last_triggered_at, filter_fn=filter_fn
        ),
        logger=logger or FakeLogger(),
    )


def rule_dict(**overrides: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    defaults: dict[str, Any] = {
        "id": "rule-1",
        "tenant_id": "tenant-1",
        "symbol": "BTCUSDT",
        "comparator": "above",
        "threshold": 50000.0,
        "status": "active",
        "interval": "1m",
        "window_seconds": None,
        "cooldown_seconds": 300,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return defaults


def candle_payload(
    symbol: str = "BTCUSDT",
    interval: str = "1m",
    open_time_ms: int = 1_710_000_000_000,
    close: float = 51000.0,
    tenant_id: str = "tenant-1",
) -> dict[str, Any]:
    return DomainEvent(
        event_type="candle_updated",
        aggregate_id=f"{symbol}:{interval}:{open_time_ms}",
        tenant_id=tenant_id,
        data={
            "symbol": symbol,
            "interval": interval,
            "open_time_ms": open_time_ms,
            "open": close - 1000.0,
            "high": close + 500.0,
            "low": close - 1500.0,
            "close": close,
            "volume": 100.0,
            "trade_count": 10,
        },
    ).to_message()


# ---------------------------------------------------------------------------
# Engine flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_above_rule_triggers_on_matching_close() -> None:
    producer = FakeProducer()
    engine = make_engine([rule_dict()], producer=producer)

    await engine._process(candle_payload(close=51000.0))

    assert len(producer.published) == 1
    topic, key, data = producer.published[0]
    assert topic == "alerts.triggers"
    assert key == "BTCUSDT"
    assert data["threshold"] == 50000.0
    assert data["current_value"] == 51000.0
    assert data["interval"] == "1m"


@pytest.mark.asyncio
async def test_above_rule_does_not_trigger_below_threshold() -> None:
    producer = FakeProducer()
    engine = make_engine([rule_dict(threshold=60000.0)], producer=producer)

    await engine._process(candle_payload(close=51000.0))

    assert len(producer.published) == 0, "should not fire when threshold not met"


@pytest.mark.asyncio
async def test_below_rule_triggers_on_low_close() -> None:
    producer = FakeProducer()
    engine = make_engine([rule_dict(comparator="below", threshold=52000.0)], producer=producer)

    await engine._process(candle_payload(close=51000.0))

    assert len(producer.published) == 1


@pytest.mark.asyncio
async def test_rule_is_only_evaluated_on_its_own_interval() -> None:
    """A 5m rule must not fire from a 1m candle event."""
    producer = FakeProducer()
    engine = make_engine([rule_dict(interval="5m")], producer=producer)

    await engine._process(candle_payload(interval="1m", close=51000.0))

    assert len(producer.published) == 0


@pytest.mark.asyncio
async def test_rule_fires_on_matching_interval() -> None:
    producer = FakeProducer()
    engine = make_engine([rule_dict(interval="5m")], producer=producer)

    await engine._process(candle_payload(interval="5m", close=51000.0))

    assert len(producer.published) == 1


@pytest.mark.asyncio
async def test_crossing_rule_uses_previous_close_from_history() -> None:
    """crosses_above fires only when the previous close was below threshold."""
    producer = FakeProducer()
    engine = make_engine([rule_dict(comparator="crosses_above", threshold=50000.0)], producer=producer)
    history: PriceHistory = engine._history

    history.append("BTCUSDT", "1m", 1_710_000_000_000, 49000.0)
    await engine._process(candle_payload(open_time_ms=1_710_000_060_000, close=50100.0))
    assert len(producer.published) == 1

    # Stays above: no new crossing.
    await engine._process(candle_payload(open_time_ms=1_710_000_120_000, close=50200.0))
    assert len(producer.published) == 1


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cooldown_suppresses_repeat_trigger() -> None:
    """A trigger fired seconds ago suppresses the next evaluation."""
    producer = FakeProducer()
    recent = datetime.now(UTC) - timedelta(seconds=10)
    engine = make_engine([rule_dict()], producer=producer, last_triggered_at=recent)

    await engine._process(candle_payload(close=51000.0))
    await engine._process(candle_payload(open_time_ms=1_710_000_060_000, close=51100.0))

    assert len(producer.published) == 0, "trigger within cooldown must be suppressed"


@pytest.mark.asyncio
async def test_trigger_fires_after_cooldown_elapsed() -> None:
    producer = FakeProducer()
    stale = datetime.now(UTC) - timedelta(seconds=400)
    engine = make_engine([rule_dict(cooldown_seconds=300)], producer=producer, last_triggered_at=stale)

    await engine._process(candle_payload(close=51000.0))

    assert len(producer.published) == 1


@pytest.mark.asyncio
async def test_no_prior_trigger_fires_immediately() -> None:
    producer = FakeProducer()
    engine = make_engine([rule_dict()], producer=producer, last_triggered_at=None)

    await engine._process(candle_payload(close=51000.0))

    assert len(producer.published) == 1


# ---------------------------------------------------------------------------
# Event routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_recognizes_watchlist_created_event() -> None:
    """A watchlist_created event produced by command-service using the shared
    schema should be accepted (not dropped as unknown)."""
    logger = FakeLogger()
    engine = make_engine(logger=logger)

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
    logger = FakeLogger()
    engine = make_engine(logger=logger)

    payload = DomainEvent(
        event_type="alert_rule_created",
        aggregate_id="rule-1",
        tenant_id="tenant-1",
        data={
            "id": "rule-1",
            "symbol": "BTCUSDT",
            "comparator": "above",
            "threshold": 50000.0,
            "interval": "1m",
            "window_seconds": None,
            "cooldown_seconds": 300,
        },
    ).to_message()

    await engine._process(payload)

    assert any(
        m["level"] == "info" and "alert_rule_created" in str(m["kwargs"])
        for m in logger.messages
    ), "expected info log for alert_rule_created"


@pytest.mark.asyncio
async def test_process_ignores_unknown_event_type() -> None:
    """Unknown event types should be logged at debug level and ignored."""
    logger = FakeLogger()
    engine = make_engine(logger=logger)

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


# ---------------------------------------------------------------------------
# Dispatcher integration: full engine flow
# ---------------------------------------------------------------------------


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
    engine = _build_engine_with_dispatcher([rule_dict()], dispatcher)

    await engine._process(candle_payload(close=51000.0))

    assert len(ch.received) == 1
    payload = ch.received[0]
    assert payload.symbol == "BTCUSDT"
    assert payload.tenant_id == "tenant-1"
    assert payload.rule_id == "rule-1"
    assert payload.comparator == "above"
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
    engine = _build_engine_with_dispatcher([rule_dict(threshold=60000.0)], dispatcher)

    await engine._process(candle_payload(close=51000.0))

    assert len(ch.received) == 0, "dispatcher should not be called for non-matching rule"


@pytest.mark.asyncio
async def test_dispatcher_called_for_multiple_matching_rules() -> None:
    """If multiple active rules match, the dispatcher is called once per rule."""
    ch = _RecordingChannel()
    dispatcher = NotificationDispatcher([ch])
    rules = [
        rule_dict(id="rule-above", comparator="above", threshold=50000.0),
        rule_dict(id="rule-below", comparator="below", threshold=52000.0),
        rule_dict(id="rule-below-2", comparator="below", threshold=51500.0),
    ]
    engine = _build_engine_with_dispatcher(rules, dispatcher)

    await engine._process(candle_payload(close=51000.0))

    # above(50000) ✓, below(52000) ✓, below(51500) ✓  → 3 triggers
    assert len(ch.received) == 3
    rule_ids = {p.rule_id for p in ch.received}
    assert rule_ids == {"rule-above", "rule-below", "rule-below-2"}


@pytest.mark.asyncio
async def test_dispatcher_called_per_symbol_independently() -> None:
    """Rules are scoped by (tenant_id, symbol). Only matching symbols fire."""
    ch = _RecordingChannel()
    dispatcher = NotificationDispatcher([ch])
    btc_rules = [rule_dict(id="rule-btc", symbol="BTCUSDT")]
    btc_factory = FakeSessionFactory(btc_rules, filter_fn=_active_only)
    engine_btc = AlertEngine(
        consumer=FakeConsumer([]),
        producer=FakeProducer(),
        alerts_topic="alerts.triggers",
        session_factory=btc_factory,
        logger=FakeLogger(),
        dispatcher=dispatcher,
    )
    await engine_btc._process(candle_payload(symbol="BTCUSDT", close=51000.0))
    assert len(ch.received) == 1
    assert ch.received[0].rule_id == "rule-btc"
    assert ch.received[0].symbol == "BTCUSDT"

    eth_rules = [rule_dict(id="rule-eth", symbol="ETHUSDT", threshold=2000.0)]
    eth_factory = FakeSessionFactory(eth_rules, filter_fn=_active_only)
    engine_eth = AlertEngine(
        consumer=FakeConsumer([]),
        producer=FakeProducer(),
        alerts_topic="alerts.triggers",
        session_factory=eth_factory,
        logger=FakeLogger(),
        dispatcher=dispatcher,
    )
    await engine_eth._process(candle_payload(symbol="ETHUSDT", close=2100.0))
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
    engine = AlertEngine(
        consumer=FakeConsumer([]),
        producer=producer,
        alerts_topic="alerts.triggers",
        session_factory=FakeSessionFactory([rule_dict()], filter_fn=_active_only),
        logger=FakeLogger(),
        dispatcher=dispatcher,
    )

    # Should not raise
    await engine._process(candle_payload(close=51000.0))

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
    engine = AlertEngine(
        consumer=FakeConsumer([]),
        producer=producer,
        alerts_topic="alerts.triggers",
        session_factory=FakeSessionFactory([rule_dict()], filter_fn=_active_only),
        logger=FakeLogger(),
        dispatcher=dispatcher,
    )

    # Should not raise despite RuntimeError from dispatcher
    await engine._process(candle_payload(close=51000.0))

    # Trigger still persisted + published
    assert len(producer.published) == 1


@pytest.mark.asyncio
async def test_dispatcher_payload_has_unique_trigger_id() -> None:
    """Each trigger dispatched must carry a unique trigger_id."""
    ch = _RecordingChannel()
    dispatcher = NotificationDispatcher([ch])
    engine = _build_engine_with_dispatcher([rule_dict()], dispatcher)

    await engine._process(candle_payload(close=51000.0))
    await engine._process(candle_payload(open_time_ms=1_710_000_060_000, close=51100.0))

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
    engine = _build_engine_with_dispatcher([rule_dict(status="paused")], dispatcher)

    await engine._process(candle_payload(close=51000.0))

    assert len(ch.received) == 0, "paused rule should not fire"
