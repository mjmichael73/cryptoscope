"""Technical indicators computed from a candle series.

These are pure functions over the closing prices so they are trivial to unit
test and free of any I/O. The query service fetches candles from ClickHouse and
then folds them through one of these.
"""

from __future__ import annotations

import math

from cryptoscope_shared.indicators import rsi_series as shared_rsi_series

from app.domain.errors import ValidationError
from app.domain.models import Candle, IndicatorPoint

SUPPORTED = {
    "sma",
    "ema",
    "volatility",
    "macd",
    "macd_signal",
    "macd_histogram",
    "bb_upper",
    "bb_middle",
    "bb_lower",
    "rsi",
}

# MACD standard constants.
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9


def compute(kind: str, candles: list[Candle], period: int) -> list[IndicatorPoint]:
    if kind not in SUPPORTED:
        raise ValidationError(f"unsupported indicator: {kind}")
    if period <= 0:
        raise ValidationError("period must be positive")

    if kind == "sma":
        return simple_moving_average(candles, period)
    if kind == "ema":
        return exponential_moving_average(candles, period)
    if kind == "volatility":
        return rolling_volatility(candles, period)
    if kind == "macd":
        return macd(candles)
    if kind == "macd_signal":
        return macd_signal(candles)
    if kind == "macd_histogram":
        return macd_histogram(candles)
    if kind == "bb_upper":
        return bollinger_upper(candles, period)
    if kind == "bb_middle":
        return bollinger_middle(candles, period)
    if kind == "bb_lower":
        return bollinger_lower(candles, period)
    return rsi(candles, period)


def _ema(values: list[float], period: int) -> list[float]:
    """EMA over raw values, seeded with the mean of the first window."""
    if len(values) < period:
        return []
    out = [sum(values[:period]) / period]
    multiplier = 2 / (period + 1)
    for value in values[period:]:
        out.append((value - out[-1]) * multiplier + out[-1])
    return out


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


def exponential_moving_average(
    candles: list[Candle], period: int
) -> list[IndicatorPoint]:
    values = [c.close for c in candles]
    ema_values = _ema(values, period)
    return [
        IndicatorPoint(candles[period - 1 + i].open_time_ms, v)
        for i, v in enumerate(ema_values)
    ]


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


def macd(candles: list[Candle]) -> list[IndicatorPoint]:
    """MACD line: EMA(12) − EMA(26) of the closes."""
    closes = [c.close for c in candles]
    fast = _ema(closes, MACD_FAST)
    slow = _ema(closes, MACD_SLOW)
    if not slow:
        return []
    offset = MACD_SLOW - MACD_FAST
    # Both EMAs start at their own window's end; align their timestamps.
    return [
        IndicatorPoint(candles[MACD_SLOW - 1 + i].open_time_ms, f - s)
        for i, (f, s) in enumerate(zip(fast[offset:], slow))
    ]


def macd_signal(candles: list[Candle]) -> list[IndicatorPoint]:
    """Signal line: EMA(9) of the MACD line."""
    line = [p.value for p in macd(candles)]
    signal_values = _ema(line, MACD_SIGNAL)
    if not signal_values:
        return []
    line_points = macd(candles)
    start = MACD_SIGNAL - 1
    return [
        IndicatorPoint(line_points[start + i].time_ms, v)
        for i, v in enumerate(signal_values)
    ]


def macd_histogram(candles: list[Candle]) -> list[IndicatorPoint]:
    """Histogram: MACD line − signal line, aligned with the signal."""
    line_points = macd(candles)
    signal_points = macd_signal(candles)
    if not signal_points:
        return []
    line_by_time = {p.time_ms: p.value for p in line_points}
    return [
        IndicatorPoint(sp.time_ms, line_by_time[sp.time_ms] - sp.value)
        for sp in signal_points
    ]


def bollinger_middle(candles: list[Candle], period: int) -> list[IndicatorPoint]:
    """Bollinger middle band: the SMA of the closes."""
    return simple_moving_average(candles, period)


def _bollinger_deviation(candles: list[Candle], period: int) -> list[float]:
    """Population stddev of the closes over each rolling window."""
    deviations: list[float] = []
    for i in range(period - 1, len(candles)):
        window = [c.close for c in candles[i - period + 1 : i + 1]]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        deviations.append(math.sqrt(variance))
    return deviations


def bollinger_upper(candles: list[Candle], period: int) -> list[IndicatorPoint]:
    middle = simple_moving_average(candles, period)
    deviations = _bollinger_deviation(candles, period)
    return [
        IndicatorPoint(mp.time_ms, mp.value + 2 * sd)
        for mp, sd in zip(middle, deviations)
    ]


def bollinger_lower(candles: list[Candle], period: int) -> list[IndicatorPoint]:
    middle = simple_moving_average(candles, period)
    deviations = _bollinger_deviation(candles, period)
    return [
        IndicatorPoint(mp.time_ms, mp.value - 2 * sd)
        for mp, sd in zip(middle, deviations)
    ]


def rsi(candles: list[Candle], period: int) -> list[IndicatorPoint]:
    """RSI over the closes, one point per close once enough history exists."""
    closes = [c.close for c in candles]
    series = shared_rsi_series(closes, period)
    return [
        IndicatorPoint(candles[i].open_time_ms, value)
        for i, value in enumerate(series)
        if value is not None
    ]
