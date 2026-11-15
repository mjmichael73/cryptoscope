from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from cryptoscope_shared.comparators import Comparator
from cryptoscope_shared.events import ALERT_RULE_DELETED, CANDLE_UPDATED, DomainEvent
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.evaluation import evaluate
from app.domain.models import AlertRule, AlertRuleStatus
from app.infra.db import AlertRuleModel, AlertTriggerModel
from app.infra.history import PriceHistory
from app.infra.notify import NotificationDispatcher, TriggerPayload


class AlertEngine:
    """Consumes domain events, evaluates rules, and fires triggers.

    Rules live in the shared ``alert_rules`` table (owned by the command
    service's migrations); the engine reads them directly and evaluates each
    rule only against candles of the rule's own interval. A per-rule cooldown
    read from the triggers table keeps sustained conditions from becoming
    notification storms.
    """

    def __init__(
        self,
        consumer: Any,
        producer: Any,
        alerts_topic: str,
        session_factory: async_sessionmaker[AsyncSession],
        logger: Any,
        dispatcher: NotificationDispatcher | None = None,
        history: PriceHistory | None = None,
    ):
        self._consumer = consumer
        self._producer = producer
        self._alerts_topic = alerts_topic
        self._session_factory = session_factory
        self._logger = logger
        self._dispatcher = dispatcher or NotificationDispatcher()
        self._history = history or PriceHistory()

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

        if event.event_type == CANDLE_UPDATED:
            await self._evaluate_candle_event(event)
        elif event.event_type == ALERT_RULE_DELETED:
            await self._mark_rule_deleted(event)
        elif event.event_type in ("watchlist_created", "alert_rule_created"):
            self._logger.info(
                "domain event received",
                event_type=event.event_type,
                tenant_id=event.tenant_id,
            )
        else:
            self._logger.debug("ignoring unknown event type", event_type=event.event_type)

    async def _mark_rule_deleted(self, event: DomainEvent) -> None:
        """Mark a deleted rule as ``deleted`` in the shared rules table.

        The command service already soft-deletes the row before publishing;
        this handler is a defensive consistency measure so a replayed or
        delayed event still disables the rule (e.g. after an outage).
        """
        rule_id = event.aggregate_id or str(event.data.get("id", ""))
        if not rule_id:
            self._logger.warning("alert_rule_deleted without rule id")
            return
        async with self._session_factory() as session:
            await session.execute(
                update(AlertRuleModel)
                .where(AlertRuleModel.id == rule_id)
                .values(status=AlertRuleStatus.DELETED.value)
            )
            await session.commit()
        self._logger.info(
            "alert rule marked deleted",
            rule_id=rule_id,
            tenant_id=event.tenant_id,
        )

    async def _evaluate_candle_event(self, event: DomainEvent) -> None:
        symbol = event.data.get("symbol", "")
        if not symbol:
            return
        interval = event.data.get("interval", "1m")
        open_time_ms = int(event.data.get("open_time_ms") or event.data.get("timestamp") or 0)
        close = float(event.data.get("close", 0.0))
        tenant_id = event.tenant_id

        self._history.append(symbol, interval, open_time_ms, close)
        closes = self._history.closes(symbol, interval)

        rules = await self._fetch_active_rules(tenant_id, symbol)
        for rule in rules:
            if rule.status != AlertRuleStatus.ACTIVE:
                continue
            if rule.interval != interval:
                continue
            if await self._cooldown_active(rule):
                self._logger.debug(
                    "trigger suppressed by cooldown",
                    rule_id=rule.id,
                    symbol=rule.symbol,
                )
                continue
            triggered, current_value = evaluate(
                rule.comparator.value, rule.threshold, rule.window_seconds, closes
            )
            if triggered:
                await self._fire_trigger(rule, current_value, tenant_id)

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
                    interval=m.interval,
                    window_seconds=m.window_seconds,
                    cooldown_seconds=m.cooldown_seconds,
                )
                for m in models
            ]

    async def _cooldown_active(self, rule: AlertRule) -> bool:
        """True when the rule fired within its cooldown window."""
        last_triggered_at = await self._last_triggered_at(rule.id)
        if last_triggered_at is None:
            return False
        elapsed = datetime.now(UTC) - last_triggered_at
        return elapsed.total_seconds() < rule.cooldown_seconds

    async def _last_triggered_at(self, rule_id: str) -> datetime | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(func.max(AlertTriggerModel.triggered_at)).where(
                    AlertTriggerModel.rule_id == rule_id
                )
            )
            return result.scalar()

    async def _fire_trigger(self, rule: AlertRule, current_value: float, tenant_id: str) -> None:
        trigger_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        trigger_data = {
            "id": trigger_id,
            "tenant_id": tenant_id,
            "rule_id": rule.id,
            "symbol": rule.symbol,
            "comparator": rule.comparator.value,
            "threshold": rule.threshold,
            "current_value": current_value,
            "interval": rule.interval,
            "window_seconds": rule.window_seconds,
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
                interval=rule.interval,
                window_seconds=rule.window_seconds,
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

        # Dispatch to notification channels (best-effort)
        try:
            payload = TriggerPayload(
                trigger_id=trigger_id,
                tenant_id=tenant_id,
                rule_id=rule.id,
                symbol=rule.symbol,
                comparator=rule.comparator.value,
                threshold=rule.threshold,
                current_value=current_value,
                triggered_at=now.isoformat(),
                interval=rule.interval,
                window_seconds=rule.window_seconds,
            )
            results = self._dispatcher.dispatch(payload)
            if results:
                self._logger.info("notifications dispatched", results=results)
        except Exception:
            self._logger.exception("notification dispatch failed")
