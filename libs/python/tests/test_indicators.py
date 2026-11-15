"""Tests for the shared technical indicator functions."""

from __future__ import annotations

import pytest

from cryptoscope_shared.indicators import rsi, rsi_series


def test_rsi_returns_none_for_short_series() -> None:
    # RSI(14) needs period + 1 prices.
    assert rsi([100.0] * 14) is None


def test_rsi_flat_series_is_neutral() -> None:
    # No gains, no losses — neutral, not zero or 100.
    assert rsi([100.0] * 15) == pytest.approx(50.0)


def test_rsi_all_gains_is_hundred() -> None:
    assert rsi([float(i) for i in range(1, 16)]) == pytest.approx(100.0)


def test_rsi_all_losses_is_zero() -> None:
    assert rsi([float(-i) for i in range(1, 16)]) == pytest.approx(0.0)


def test_rsi_respects_custom_period() -> None:
    # RSI(2) over 3 prices: one gain then one loss.
    assert rsi([1.0, 2.0, 1.0], period=2) is not None


def test_rsi_matches_known_wilder_value() -> None:
    # Hand-computed Wilder RSI(2) for [1, 2, 1]: avg_gain = avg_loss = 0.5 → 50.
    assert rsi([1.0, 2.0, 1.0], period=2) == pytest.approx(50.0)


def test_rsi_series_matches_rsi_on_every_prefix() -> None:
    prices = [float(i) * (1 if i % 3 else -1) for i in range(30)]
    series = rsi_series(prices, period=5)
    # Aligned with the input: None until enough history, then the same value
    # a fresh rsi() call over the prefix would return.
    assert len(series) == len(prices)
    assert all(v is None for v in series[:5])
    for i in range(5, len(prices)):
        assert series[i] == pytest.approx(rsi(prices[: i + 1], period=5))


def test_rsi_series_short_input_is_all_none() -> None:
    assert rsi_series([1.0, 2.0], period=14) == [None, None]
    assert rsi_series([], period=14) == []
