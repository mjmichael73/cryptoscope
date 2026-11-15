"""Tests for the shared alert-rule comparator vocabulary."""

from __future__ import annotations

import pytest

from cryptoscope_shared.comparators import (
    ALLOWED_INTERVALS,
    Comparator,
    validate_rule_params,
    window_required,
)


def test_comparator_covers_all_eight_kinds() -> None:
    assert {c.value for c in Comparator} == {
        "above",
        "below",
        "crosses_above",
        "crosses_below",
        "pct_change_above",
        "pct_change_below",
        "rsi_above",
        "rsi_below",
    }


@pytest.mark.parametrize(
    ("comparator", "expected"),
    [
        ("above", False),
        ("below", False),
        ("crosses_above", False),
        ("crosses_below", False),
        ("pct_change_above", True),
        ("pct_change_below", True),
        ("rsi_above", False),
        ("rsi_below", False),
    ],
)
def test_window_required_only_for_pct_change(comparator: str, expected: bool) -> None:
    assert window_required(comparator) is expected


def test_validate_accepts_pct_change_with_window() -> None:
    validate_rule_params("pct_change_below", 3600)


@pytest.mark.parametrize("window", [None, 30, 90000])
def test_validate_rejects_bad_pct_change_window(window: int | None) -> None:
    with pytest.raises(ValueError):
        validate_rule_params("pct_change_below", window)


def test_validate_rejects_window_on_price_comparator() -> None:
    with pytest.raises(ValueError):
        validate_rule_params("above", 3600)


def test_validate_accepts_price_comparator_without_window() -> None:
    validate_rule_params("above", None)


def test_validate_rejects_unknown_comparator() -> None:
    with pytest.raises(ValueError):
        validate_rule_params("sideways", None)


def test_allowed_intervals_match_stream_processor_output() -> None:
    # The stream-processor aggregates 1m, 5m and 1h candles; a rule for any
    # other interval would never be evaluated.
    assert ALLOWED_INTERVALS == {"1m", "5m", "1h"}
