from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

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

    def all(self) -> list[dict[str, Any]]:
        return self._rules

    def scalar_one_or_none(self) -> dict[str, Any] | None:
        return self._rules[0] if self._rules else None


class FakeLogger:
    def info(self, *args: Any, **kwargs: Any) -> None:
        pass

    def debug(self, *args: Any, **kwargs: Any) -> None:
        pass

    def warning(self, *args: Any, **kwargs: Any) -> None:
        pass

    def error(self, *args: Any, **kwargs: Any) -> None:
        pass

    def exception(self, *args: Any, **kwargs: Any) -> None:
        pass
