from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from cryptoscope_shared.events import DomainEvent  # noqa: F401 — re-exported for test imports


class Comparator(str, Enum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"


class AlertRuleStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    TRIGGERED = "triggered"


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
