"""Read-side value types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candle:
    open_time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class IndicatorPoint:
    time_ms: int
    value: float


@dataclass(frozen=True)
class SymbolSummary:
    """Historical coverage of one symbol in the candle store."""

    symbol: str
    first_open_time_ms: int
    last_open_time_ms: int
    candle_count: int
    intervals: list[str]
