"""Shared alert-rule comparator vocabulary.

The command service validates and stores alert rules with these values and the
alert service evaluates them, so both sides must agree on the exact strings.
This module is the single source of truth; neither service defines its own
comparator list.

Semantics (evaluated by the alert service over a rolling series of closes):

- ``above`` / ``below``          — current close vs threshold
- ``crosses_above``              — previous close <= threshold and current close > threshold
- ``crosses_below``              — previous close >= threshold and current close < threshold
- ``pct_change_above`` / ``_below`` — percent change over ``window_seconds`` crosses
  +/-threshold (threshold is a positive percentage)
- ``rsi_above`` / ``rsi_below``  — RSI(14) of the rolling close window vs threshold
"""

from __future__ import annotations

from enum import Enum

# Intervals the stream-processor actually emits candle_updated events for.
# A rule outside this set would never be evaluated.
ALLOWED_INTERVALS = {"1m", "5m", "1h"}

# pct_change windows: at least one minute, at most one day.
MIN_WINDOW_SECONDS = 60
MAX_WINDOW_SECONDS = 86400


class Comparator(str, Enum):
    ABOVE = "above"
    BELOW = "below"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"
    PCT_CHANGE_ABOVE = "pct_change_above"
    PCT_CHANGE_BELOW = "pct_change_below"
    RSI_ABOVE = "rsi_above"
    RSI_BELOW = "rsi_below"


def window_required(comparator: str) -> bool:
    """Whether the comparator needs a ``window_seconds`` parameter."""
    return comparator in (Comparator.PCT_CHANGE_ABOVE.value, Comparator.PCT_CHANGE_BELOW.value)


def validate_rule_params(comparator: str, window_seconds: int | None) -> None:
    """Validate the comparator/window pairing. Raises ValueError when invalid."""
    try:
        Comparator(comparator)
    except ValueError as exc:
        raise ValueError(f"unknown comparator: {comparator}") from exc

    if window_required(comparator):
        if window_seconds is None:
            raise ValueError(f"{comparator} requires window_seconds")
        if not MIN_WINDOW_SECONDS <= window_seconds <= MAX_WINDOW_SECONDS:
            raise ValueError(
                f"window_seconds must be between {MIN_WINDOW_SECONDS} and {MAX_WINDOW_SECONDS}"
            )
    elif window_seconds is not None:
        raise ValueError(f"{comparator} does not take window_seconds")
