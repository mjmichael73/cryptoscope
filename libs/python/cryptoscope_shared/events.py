"""Shared domain event schema for the cryptoscope platform.

This is the single source of truth for the event envelope that crosses the
Kafka bus between services. Every domain event producer and consumer uses this
schema so field names and event types stay in sync.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    tenant_id: str
    data: dict[str, Any]
    aggregate_id: str = ""
    timestamp: int = 0

    def __post_init__(self) -> None:
        if self.timestamp == 0:
            object.__setattr__(self, "timestamp", int(time.time()))

    def to_message(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "tenant_id": self.tenant_id,
            "data": self.data,
            "timestamp": self.timestamp,
        }


WATCHLIST_CREATED = "watchlist_created"
ALERT_RULE_CREATED = "alert_rule_created"
CANDLE_UPDATED = "candle_updated"
WATCHLIST_UPDATED = "watchlist_updated"
WATCHLIST_DELETED = "watchlist_deleted"
ALERT_RULE_DELETED = "alert_rule_deleted"
