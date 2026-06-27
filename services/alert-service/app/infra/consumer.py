from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from cryptoscope_shared.kafka import JsonConsumer, JsonProducer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.errors import EvaluationError
from app.domain.models import AlertRule, AlertRuleStatus, AlertTrigger, Comparator, DomainEvent
from app.infra.db import AlertRuleModel, AlertTriggerModel


class AlertEngine:
    def __init__(
        self,
        consumer: JsonConsumer,
        producer: JsonProducer,
        alerts_topic: str,
        session_factory: async_sessionmaker[AsyncSession],
        logger: Any,
    ):
        self._consumer = consumer
        self._producer = producer
        self._alerts_topic = alerts_topic
        self._session_factory = session_factory
        self._logger = logger

    async def run(self) -> None:
        self._logger.info("alert engine starting")
        async for key, payload in self._consumer.messages():
            try:
                await self._process(payload)
            except Exception:
                self._logger.exception("failed to process message, skipping")

    async def _process(self, payload: dict[str, Any]) -> None:
        event = DomainEvent(
            event_type=payload.get("event_type", ""),
            aggregate_id=payload.get("aggregate_id", ""),
            tenant_id=payload.get("tenant_id", ""),
            data=payload.get("data", {}),
            timestamp=payload.get("timestamp", 0),
        )

        if event.event_type == "candle_updated":
            await self._evaluate_candle_event(event)
        elif event.event_type in ("watchlist_created", "alert_rule_created"):
            self._logger.info(
                "domain event received",
                event_type=event.event_type,
                tenant_id=event.tenant_id,
            )
        else:
            self._logger.debug("ignoring unknown event type", event_type=event.event_type)

    async def _evaluate_candle_event(self, event: DomainEvent) -> None:
        symbol = event.data.get("symbol", "")
        close = event.data.get("close", 0.0)
        tenant_id = event.tenant_id

        rules = await self._fetch_active_rules(tenant_id, symbol)
        for rule in rules:
            triggered = self._evaluate_rule(rule, close)
            if triggered:
                await self._fire_trigger(rule, close, tenant_id)

    async def _fetch_active_rules(self, tenant_id: str, symbol: str) -> list[AlertRule]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AlertRuleModel).where(
                    AlertRuleModel.tenant_id == tenant_id,
                    AlertRuleModel.symbol == symbol,
                    AlertRuleModel.status == "active",
                )
            )
            models = result.scalars().all()
            return [
                AlertRule(
                    id=m.id,
                    tenant_id=m.tenant_id,
                    symbol=m.symbol,
                    comparator=Comparator(m.comparator),
                    threshold=m.threshold,
                    status=AlertRuleStatus(m.status),
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                )
                for m in models
            ]

    def _evaluate_rule(self, rule: AlertRule, current_value: float) -> bool:
        if rule.comparator == Comparator.GT:
            return current_value > rule.threshold
        elif rule.comparator == Comparator.GTE:
            return current_value >= rule.threshold
        elif rule.comparator == Comparator.LT:
            return current_value < rule.threshold
        elif rule.comparator == Comparator.LTE:
            return current_value <= rule.threshold
        elif rule.comparator == Comparator.EQ:
            return abs(current_value - rule.threshold) < 0.0001
        return False

    async def _fire_trigger(self, rule: AlertRule, current_value: float, tenant_id: str) -> None:
        trigger_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        trigger_data = {
            "id": trigger_id,
            "tenant_id": tenant_id,
            "rule_id": rule.id,
            "symbol": rule.symbol,
            "comparator": rule.comparator.value,
            "threshold": rule.threshold,
            "current_value": current_value,
            "triggered_at": now.isoformat(),
        }

        async with self._session_factory() as session:
            trigger = AlertTriggerModel(
                id=trigger_id,
                tenant_id=tenant_id,
                rule_id=rule.id,
                symbol=rule.symbol,
                comparator=rule.comparator.value,
                threshold=rule.threshold,
                current_value=current_value,
                triggered_at=now,
            )
            session.add(trigger)
            await session.commit()

        await self._producer.publish(self._alerts_topic, rule.symbol, trigger_data)
        self._logger.info(
            "alert triggered",
            rule_id=rule.id,
            symbol=rule.symbol,
            value=current_value,
            threshold=rule.threshold,
        )
