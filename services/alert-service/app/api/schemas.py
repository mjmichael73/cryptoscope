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


class HealthResponse(BaseModel):
    status: str
