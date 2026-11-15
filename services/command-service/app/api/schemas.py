"""Request and response models for the command API."""

from __future__ import annotations

from cryptoscope_shared.comparators import ALLOWED_INTERVALS
from pydantic import BaseModel, Field, field_validator


class CreateWatchlistRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    symbols: list[str] = Field(default_factory=list)


class CreateAlertRuleRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    comparator: str = Field(
        pattern="^(above|below|crosses_above|crosses_below|pct_change_above|pct_change_below|rsi_above|rsi_below)$"
    )
    threshold: float
    interval: str = "1m"
    window_seconds: int | None = Field(default=None, ge=60, le=86400)
    cooldown_seconds: int = Field(default=300, ge=1)

    @field_validator("interval")
    @classmethod
    def interval_must_be_supported(cls, value: str) -> str:
        if value not in ALLOWED_INTERVALS:
            raise ValueError(f"interval must be one of: {', '.join(sorted(ALLOWED_INTERVALS))}")
        return value


class AlertTemplateOut(BaseModel):
    id: str
    name: str
    description: str
    comparator: str
    threshold: float | None
    window_seconds: int | None
    interval: str
    cooldown_seconds: int


class CreatedResponse(BaseModel):
    id: str
