"""Pure evaluation functions for alert rules.

Every comparator is evaluated over a rolling series of closes so the logic is
free of I/O and trivially unit-testable. The engine feeds each rule the close
history for the rule's interval and gets back ``(triggered, current_value)``.

These functions never raise for insufficient data — a rule quietly stays
untriggered until enough closes exist (documented warm-up after a restart).
"""

from __future__ import annotations

# A close observation: (candle open time in ms, close price).
Close = tuple[int, float]

from cryptoscope_shared.indicators import rsi

RSI_PERIOD = 14


def evaluate(
    comparator: str,
    threshold: float,
    window_seconds: int | None,
    closes: list[Close],
) -> tuple[bool, float]:
    """Evaluate one rule against the close series.

    Returns ``(triggered, current_value)`` where ``current_value`` is the
    number that was compared (close price, percent change, or RSI) — it goes
    into the trigger record and notifications.
    """
    if not closes:
        return False, 0.0

    if comparator == "above":
        current = closes[-1][1]
        return current > threshold, current

    if comparator == "below":
        current = closes[-1][1]
        return current < threshold, current

    if comparator == "crosses_above":
        if len(closes) < 2:
            return False, closes[-1][1]
        previous, current = closes[-2][1], closes[-1][1]
        return previous <= threshold < current, current

    if comparator == "crosses_below":
        if len(closes) < 2:
            return False, closes[-1][1]
        previous, current = closes[-2][1], closes[-1][1]
        return previous >= threshold > current, current

    if comparator in ("pct_change_above", "pct_change_below"):
        return _evaluate_pct_change(comparator, threshold, window_seconds, closes)

    if comparator in ("rsi_above", "rsi_below"):
        return _evaluate_rsi(comparator, threshold, closes)

    # Unknown comparator: never fire rather than crash the engine.
    return False, closes[-1][1]


def _evaluate_pct_change(
    comparator: str,
    threshold: float,
    window_seconds: int | None,
    closes: list[Close],
) -> tuple[bool, float]:
    window_ms = (window_seconds or 0) * 1000
    current_time, current = closes[-1]
    baseline = None
    for open_time_ms, close in reversed(closes[:-1]):
        if open_time_ms <= current_time - window_ms:
            baseline = close
            break
    if baseline is None or baseline == 0:
        return False, current
    pct_change = (current - baseline) / baseline * 100.0
    if comparator == "pct_change_above":
        return pct_change >= threshold, pct_change
    return pct_change <= -threshold, pct_change


def _evaluate_rsi(
    comparator: str,
    threshold: float,
    closes: list[Close],
) -> tuple[bool, float]:
    value = rsi([close for _, close in closes])
    if value is None:
        # Not enough history for RSI(14) yet — report the latest close.
        return False, closes[-1][1]
    if comparator == "rsi_above":
        return value > threshold, value
    return value < threshold, value
