"""Tests for the pure alert-rule evaluation functions."""

from __future__ import annotations

import pytest

from app.domain.evaluation import evaluate, rsi

MINUTE_MS = 60_000
HOUR_MS = 3_600_000


def closes(*prices: float, start_ms: int = 1_700_000_000_000, step_ms: int = MINUTE_MS):
    """Build a (open_time_ms, close) series, oldest first."""
    return [(start_ms + i * step_ms, price) for i, price in enumerate(prices)]


# ---------------------------------------------------------------------------
# Price level comparators
# ---------------------------------------------------------------------------


def test_above_triggers_when_close_above_threshold() -> None:
    assert evaluate("above", 100.0, None, closes(99.0, 101.0)) == (True, 101.0)


def test_above_does_not_trigger_at_threshold() -> None:
    assert evaluate("above", 100.0, None, closes(100.0)) == (False, 100.0)


def test_below_triggers_when_close_below_threshold() -> None:
    assert evaluate("below", 100.0, None, closes(101.0, 99.0)) == (True, 99.0)


def test_no_data_never_triggers() -> None:
    assert evaluate("above", 100.0, None, []) == (False, 0.0)


# ---------------------------------------------------------------------------
# Crossing comparators
# ---------------------------------------------------------------------------


def test_crosses_above_triggers_on_upward_cross() -> None:
    assert evaluate("crosses_above", 100.0, None, closes(99.0, 101.0)) == (True, 101.0)


def test_crosses_above_ignores_staying_above() -> None:
    assert evaluate("crosses_above", 100.0, None, closes(101.0, 102.0)) == (False, 102.0)


def test_crosses_above_ignores_staying_below() -> None:
    assert evaluate("crosses_above", 100.0, None, closes(98.0, 99.0)) == (False, 99.0)


def test_crosses_below_triggers_on_downward_cross() -> None:
    assert evaluate("crosses_below", 100.0, None, closes(101.0, 99.0)) == (True, 99.0)


def test_crosses_below_ignores_staying_below() -> None:
    assert evaluate("crosses_below", 100.0, None, closes(99.0, 98.0)) == (False, 98.0)


def test_crossing_needs_two_closes() -> None:
    assert evaluate("crosses_above", 100.0, None, closes(101.0)) == (False, 101.0)


# ---------------------------------------------------------------------------
# Percent-change comparators
# ---------------------------------------------------------------------------


def test_pct_change_below_triggers_on_big_drop() -> None:
    series = closes(100.0, start_ms=1_700_000_000_000)
    series += closes(94.0, start_ms=1_700_000_000_000 + HOUR_MS + MINUTE_MS)
    assert evaluate("pct_change_below", 5.0, 3600, series) == (True, -6.0)


def test_pct_change_below_ignores_small_drop() -> None:
    series = closes(100.0)
    series += closes(95.5, start_ms=1_700_000_000_000 + HOUR_MS + MINUTE_MS)
    assert evaluate("pct_change_below", 5.0, 3600, series) == (False, -4.5)


def test_pct_change_above_triggers_on_big_rally() -> None:
    series = closes(100.0)
    series += closes(106.0, start_ms=1_700_000_000_000 + HOUR_MS + MINUTE_MS)
    assert evaluate("pct_change_above", 5.0, 3600, series) == (True, 6.0)


def test_pct_change_requires_history_older_than_window() -> None:
    # Only 2 minutes of history: no baseline a full hour back exists yet.
    assert evaluate("pct_change_below", 5.0, 3600, closes(100.0, 90.0)) == (False, 90.0)


def test_pct_change_uses_latest_close_within_window_as_baseline() -> None:
    start = 1_700_000_000_000
    series = [(start, 100.0), (start + 2 * MINUTE_MS, 98.0)]
    series.append((start + HOUR_MS + MINUTE_MS, 93.1))
    # Baseline is the 100.0 close (the 98.0 close is newer than now-window).
    triggered, value = evaluate("pct_change_below", 5.0, 3600, series)
    assert triggered is True
    assert value == pytest.approx(-6.9)


# ---------------------------------------------------------------------------
# RSI comparators
# ---------------------------------------------------------------------------


def test_rsi_above_triggers_on_rising_series() -> None:
    rising = [100.0 + i for i in range(20)]
    assert evaluate("rsi_above", 70.0, None, closes(*rising)) == (True, 100.0)


def test_rsi_below_triggers_on_falling_series() -> None:
    falling = [200.0 - i for i in range(20)]
    assert evaluate("rsi_below", 30.0, None, closes(*falling)) == (True, 0.0)


def test_rsi_needs_period_plus_one_closes() -> None:
    rising = [100.0 + i for i in range(14)]  # one short of RSI(14)
    triggered, value = evaluate("rsi_above", 70.0, None, closes(*rising))
    assert triggered is False
    assert value == rising[-1]


def test_rsi_flat_series_is_neutral() -> None:
    flat = [100.0] * 20
    assert evaluate("rsi_above", 70.0, None, closes(*flat)) == (False, 50.0)
    assert evaluate("rsi_below", 30.0, None, closes(*flat)) == (False, 50.0)


def test_rsi_balanced_series_is_fifty() -> None:
    series = [100.0 + (i % 2) for i in range(15)]  # 7 gains, 7 losses of 1.0
    assert rsi(series) == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------


def test_unknown_comparator_never_triggers() -> None:
    assert evaluate("sideways", 1.0, None, closes(2.0)) == (False, 2.0)


def test_rsi_returns_none_for_short_series() -> None:
    assert rsi([100.0, 101.0]) is None
