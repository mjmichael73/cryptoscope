"""Unit tests for the technical indicators."""

from __future__ import annotations

import math

import pytest

from app.domain import indicators
from app.domain.errors import ValidationError
from tests.conftest import make_candles


def test_sma_matches_hand_computed_window():
    candles = make_candles([1, 2, 3, 4, 5])
    points = indicators.simple_moving_average(candles, 3)

    values = [p.value for p in points]
    assert values == [2.0, 3.0, 4.0]
    # The first point is timestamped at the close of the first full window.
    assert points[0].time_ms == candles[2].open_time_ms


def test_sma_needs_a_full_window():
    candles = make_candles([1, 2])
    assert indicators.simple_moving_average(candles, 3) == []


def test_ema_seeds_with_the_simple_average():
    candles = make_candles([1, 2, 3, 4])
    points = indicators.exponential_moving_average(candles, 2)

    # Seed is the mean of the first two closes, then it follows the recurrence.
    assert points[0].value == pytest.approx(1.5)
    multiplier = 2 / 3
    expected = 1.5
    for close in (3, 4):
        expected = (close - expected) * multiplier + expected
    assert points[-1].value == pytest.approx(expected)


def test_volatility_is_the_rolling_stddev():
    candles = make_candles([2, 4, 6])
    points = indicators.rolling_volatility(candles, 3)

    mean = 4.0
    variance = ((2 - mean) ** 2 + (4 - mean) ** 2 + (6 - mean) ** 2) / 3
    assert points[0].value == pytest.approx(math.sqrt(variance))


def test_compute_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        indicators.compute("momentum", make_candles([1, 2, 3]), 2)


def test_compute_rejects_non_positive_period():
    with pytest.raises(ValidationError):
        indicators.compute("sma", make_candles([1, 2, 3]), 0)


# --- helpers -----------------------------------------------------------------


def _ema_series(values: list[float], period: int) -> list[float]:
    """Reference EMA: seeded with the mean of the first window."""
    out = [sum(values[:period]) / period]
    m = 2 / (period + 1)
    for v in values[period:]:
        out.append((v - out[-1]) * m + out[-1])
    return out


# --- MACD --------------------------------------------------------------------


def test_macd_line_is_ema12_minus_ema26():
    closes = [float(i) for i in range(1, 41)]  # 40 candles
    candles = make_candles(closes)
    points = indicators.macd(candles)

    fast = _ema_series(closes, 12)
    slow = _ema_series(closes, 26)
    # MACD line starts where the slower EMA starts (candle 26). The EMA
    # arrays align at the offset between their periods.
    expected = [f - s for f, s in zip(fast[26 - 12 :], slow)]
    assert [p.value for p in points] == pytest.approx(expected)
    assert points[0].time_ms == candles[25].open_time_ms


def test_macd_needs_26_candles():
    assert indicators.macd(make_candles([1.0] * 25)) == []


def test_macd_signal_is_ema9_of_the_macd_line():
    closes = [float(i) for i in range(1, 41)]
    candles = make_candles(closes)
    macd_points = indicators.macd(candles)
    signal_points = indicators.macd_signal(candles)

    macd_values = [p.value for p in macd_points]
    expected = _ema_series(macd_values, 9)
    assert [p.value for p in signal_points] == pytest.approx(expected)
    # First signal point lands on the 9th MACD point.
    assert signal_points[0].time_ms == macd_points[8].time_ms


def test_macd_signal_needs_34_candles():
    assert indicators.macd_signal(make_candles([1.0] * 33)) == []


def test_macd_histogram_is_line_minus_signal():
    closes = [float(i) for i in range(1, 41)]
    candles = make_candles(closes)
    macd_points = indicators.macd(candles)
    signal_points = indicators.macd_signal(candles)
    hist_points = indicators.macd_histogram(candles)

    # Histogram aligns with the signal's timestamps.
    assert len(hist_points) == len(signal_points)
    assert [p.time_ms for p in hist_points] == [p.time_ms for p in signal_points]
    macd_by_time = {p.time_ms: p.value for p in macd_points}
    for hp in hist_points:
        signal_value = next(
            sp.value for sp in signal_points if sp.time_ms == hp.time_ms
        )
        assert hp.value == pytest.approx(macd_by_time[hp.time_ms] - signal_value)


# --- Bollinger Bands ---------------------------------------------------------


def test_bollinger_middle_is_the_sma():
    candles = make_candles([1.0, 2.0, 3.0, 4.0, 5.0])
    middle = indicators.bollinger_middle(candles, 3)
    sma = indicators.simple_moving_average(candles, 3)
    assert [(p.time_ms, p.value) for p in middle] == [
        (p.time_ms, p.value) for p in sma
    ]


def test_bollinger_bands_are_two_stddevs_around_the_middle():
    closes = [2.0, 4.0, 6.0, 8.0, 10.0]
    candles = make_candles(closes)
    upper = indicators.bollinger_upper(candles, 3)
    middle = indicators.bollinger_middle(candles, 3)
    lower = indicators.bollinger_lower(candles, 3)

    # First window [2, 4, 6]: mean 4, population stddev sqrt(8/3).
    mean = 4.0
    variance = ((2 - mean) ** 2 + (4 - mean) ** 2 + (6 - mean) ** 2) / 3
    sd = math.sqrt(variance)
    assert upper[0].value == pytest.approx(mean + 2 * sd)
    assert middle[0].value == pytest.approx(mean)
    assert lower[0].value == pytest.approx(mean - 2 * sd)
    # All three bands share timestamps.
    assert [p.time_ms for p in upper] == [p.time_ms for p in middle]
    assert [p.time_ms for p in lower] == [p.time_ms for p in middle]


def test_bollinger_needs_a_full_window():
    assert indicators.bollinger_upper(make_candles([1.0, 2.0]), 3) == []
    assert indicators.bollinger_lower(make_candles([1.0, 2.0]), 3) == []


# --- RSI ---------------------------------------------------------------------


def test_rsi_delegates_to_the_shared_implementation():
    # Flat series is neutral 50; needs period + 1 closes.
    points = indicators.rsi(make_candles([100.0] * 15), 14)
    assert [p.value for p in points] == pytest.approx([50.0])


def test_rsi_needs_period_plus_one_closes():
    assert indicators.rsi(make_candles([100.0] * 14), 14) == []
