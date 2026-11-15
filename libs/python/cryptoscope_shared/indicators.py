"""Pure technical indicator functions shared across services.

These are functions over plain price series — free of I/O and transport
concerns — so any service (query, alert, future consumers) folds its data
through the same math.
"""

from __future__ import annotations


def rsi(prices: list[float], period: int = 14) -> float | None:
    """Wilder's RSI over a close-price series, or None when too short."""
    if len(prices) < period + 1:
        return None

    gains = losses = 0.0
    for i in range(1, period + 1):
        change = prices[i] - prices[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period

    for i in range(period + 1, len(prices)):
        change = prices[i] - prices[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0.0)) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def rsi_series(
    prices: list[float], period: int = 14
) -> list[float | None]:
    """Wilder's RSI at every position, aligned with the input.

    Positions before the first full window are ``None``. One pass — O(n) —
    so callers can run it over a whole candle series without paying the
    per-point cost of calling :func:`rsi` repeatedly.
    """
    n = len(prices)
    if n < period + 1:
        return [None] * n

    out: list[float | None] = [None] * n

    gains = losses = 0.0
    for i in range(1, period + 1):
        change = prices[i] - prices[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period

    def _value() -> float:
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        rs = avg_gain / avg_loss
        return 100.0 - 100.0 / (1.0 + rs)

    out[period] = _value()

    for i in range(period + 1, n):
        change = prices[i] - prices[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0.0) * 1.0) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0.0) * 1.0) / period
        out[i] = _value()

    return out
