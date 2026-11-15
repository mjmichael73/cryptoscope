"""Response models for the query API."""

from __future__ import annotations

from pydantic import BaseModel


class CandleOut(BaseModel):
    open_time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class IndicatorPointOut(BaseModel):
    time_ms: int
    value: float


class SymbolsOut(BaseModel):
    symbols: list[str]


class SymbolSummaryOut(BaseModel):
    symbol: str
    first_open_time_ms: int
    last_open_time_ms: int
    candle_count: int
    intervals: list[str]


class SymbolSearchOut(BaseModel):
    symbols: list[SymbolSummaryOut]
