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
        indicators.compute("macd", make_candles([1, 2, 3]), 2)


def test_compute_rejects_non_positive_period():
    with pytest.raises(ValidationError):
        indicators.compute("sma", make_candles([1, 2, 3]), 0)
