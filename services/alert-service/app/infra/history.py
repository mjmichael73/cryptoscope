"""In-memory rolling close history for the alert engine.

The engine keeps the last N closes per (symbol, interval) built purely from
candle_updated events. Crossing, percent-change and RSI comparators read from
this series. After a restart the windows refill as candles close, so those
comparators warm up within roughly one window of wall time — a documented
trade-off for keeping the alert service free of extra infrastructure.
"""

from __future__ import annotations

from collections import deque

from app.domain.evaluation import Close

DEFAULT_MAXLEN = 480


class PriceHistory:
    def __init__(self, maxlen: int = DEFAULT_MAXLEN) -> None:
        self._maxlen = maxlen
        self._series: dict[tuple[str, str], deque[Close]] = {}

    def append(self, symbol: str, interval: str, open_time_ms: int, close: float) -> None:
        key = (symbol, interval)
        if key not in self._series:
            self._series[key] = deque(maxlen=self._maxlen)
        self._series[key].append((open_time_ms, close))

    def closes(self, symbol: str, interval: str) -> list[Close]:
        """Snapshot of the series, oldest first."""
        return list(self._series.get((symbol, interval), ()))
