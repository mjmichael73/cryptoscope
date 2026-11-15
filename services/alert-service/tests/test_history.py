"""Tests for the in-memory rolling price history."""

from __future__ import annotations

from app.infra.history import PriceHistory


def test_closes_returns_series_oldest_first() -> None:
    history = PriceHistory()
    history.append("BTCUSDT", "1m", 1_000, 100.0)
    history.append("BTCUSDT", "1m", 2_000, 101.0)

    assert history.closes("BTCUSDT", "1m") == [(1_000, 100.0), (2_000, 101.0)]


def test_series_are_isolated_per_symbol_and_interval() -> None:
    history = PriceHistory()
    history.append("BTCUSDT", "1m", 1_000, 100.0)
    history.append("ETHUSDT", "1m", 1_000, 3_000.0)
    history.append("BTCUSDT", "1h", 1_000, 99.0)

    assert history.closes("BTCUSDT", "1m") == [(1_000, 100.0)]
    assert history.closes("ETHUSDT", "1m") == [(1_000, 3_000.0)]
    assert history.closes("BTCUSDT", "1h") == [(1_000, 99.0)]


def test_maxlen_evicts_oldest_closes() -> None:
    history = PriceHistory(maxlen=3)
    for i in range(1, 5):
        history.append("BTCUSDT", "1m", i * 1_000, float(i))

    assert history.closes("BTCUSDT", "1m") == [
        (2_000, 2.0),
        (3_000, 3.0),
        (4_000, 4.0),
    ]


def test_unknown_series_is_empty() -> None:
    history = PriceHistory()
    assert history.closes("BTCUSDT", "5m") == []
