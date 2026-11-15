from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from cryptoscope_shared.comparators import Comparator  # re-exported for service imports
from cryptoscope_shared.events import DomainEvent  # noqa: F401 — re-exported for test imports


class AlertRuleStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    TRIGGERED = "triggered"
    DELETED = "deleted"


@dataclass
class AlertRule:
    id: str
    tenant_id: str
    symbol: str
    comparator: Comparator
    threshold: float
    status: AlertRuleStatus
    created_at: datetime
    updated_at: datetime
    interval: str = "1m"
    window_seconds: int | None = None
    cooldown_seconds: int = 300


@dataclass
class AlertTrigger:
    id: str
    tenant_id: str
    rule_id: str
    symbol: str
    comparator: Comparator
    threshold: float
    current_value: float
    triggered_at: datetime
    acknowledged: bool
    interval: str = "1m"
    window_seconds: int | None = None


@dataclass
class CandleUpdate:
    symbol: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int
