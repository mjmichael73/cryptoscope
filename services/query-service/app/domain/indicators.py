"""Technical indicators computed from a candle series.

These are pure functions over the closing prices so they are trivial to unit
test and free of any I/O. The query service fetches candles from ClickHouse and
then folds them through one of these.
"""

from __future__ import annotations

import math

from app.domain.errors import ValidationError
from app.domain.models import Candle, IndicatorPoint

SUPPORTED = {"sma", "ema", "volatility"}


def compute(kind: str, candles: list[Candle], period: int) -> list[IndicatorPoint]:
    if kind not in SUPPORTED:
        raise ValidationError(f"unsupported indicator: {kind}")
    if period <= 0:
        raise ValidationError("period must be positive")

    if kind == "sma":
        return simple_moving_average(candles, period)
    if kind == "ema":
        return exponential_moving_average(candles, period)
    return rolling_volatility(candles, period)


def simple_moving_average(candles: list[Candle], period: int) -> list[IndicatorPoint]:
    if len(candles) < period:
        return []
    points: list[IndicatorPoint] = []
    window_sum = sum(c.close for c in candles[:period])
    points.append(IndicatorPoint(candles[period - 1].open_time_ms, window_sum / period))
    for i in range(period, len(candles)):
        window_sum += candles[i].close - candles[i - period].close
        points.append(IndicatorPoint(candles[i].open_time_ms, window_sum / period))
    return points


def exponential_moving_average(candles: list[Candle], period: int) -> list[IndicatorPoint]:
    if len(candles) < period:
        return []
    multiplier = 2 / (period + 1)
    # Seed the EMA with the simple average of the first window.
    ema = sum(c.close for c in candles[:period]) / period
    points = [IndicatorPoint(candles[period - 1].open_time_ms, ema)]
    for candle in candles[period:]:
        ema = (candle.close - ema) * multiplier + ema
        points.append(IndicatorPoint(candle.open_time_ms, ema))
    return points


def rolling_volatility(candles: list[Candle], period: int) -> list[IndicatorPoint]:
    """Standard deviation of close prices over a rolling window."""

    if len(candles) < period:
        return []
    points: list[IndicatorPoint] = []
    for i in range(period - 1, len(candles)):
        window = [c.close for c in candles[i - period + 1 : i + 1]]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        points.append(IndicatorPoint(candles[i].open_time_ms, math.sqrt(variance)))
    return points
