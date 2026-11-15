from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AlertRuleOut(BaseModel):
    id: str
    tenant_id: str
    symbol: str
    comparator: str
    threshold: float
    status: str
    created_at: datetime
    updated_at: datetime
    interval: str = "1m"
    window_seconds: int | None = None
    cooldown_seconds: int = 300


class AlertTriggerOut(BaseModel):
    id: str
    tenant_id: str
    rule_id: str
    symbol: str
    comparator: str
    threshold: float
    current_value: float
    triggered_at: datetime
    acknowledged: bool
    interval: str = "1m"
    window_seconds: int | None = None


class HealthResponse(BaseModel):
    status: str
