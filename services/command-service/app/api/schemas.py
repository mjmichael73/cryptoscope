"""Request and response models for the command API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateWatchlistRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    symbols: list[str] = Field(default_factory=list)


class CreateAlertRuleRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    comparator: str = Field(pattern="^(above|below)$")
    threshold: float


class CreatedResponse(BaseModel):
    id: str
