"""Fixtures for the query service tests."""

from __future__ import annotations

import pytest

from app.domain.models import Candle

TENANT_ID = "11111111-1111-1111-1111-111111111111"


def make_candles(closes: list[float], start_ms: int = 0, step_ms: int = 60_000) -> list[Candle]:
    return [
        Candle(
            open_time_ms=start_ms + i * step_ms,
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1.0,
        )
        for i, close in enumerate(closes)
    ]


class FakeReadRepository:
    def __init__(self, candles: list[Candle] | None = None, symbols: list[str] | None = None) -> None:
        self._candles = candles or []
        self._symbols = symbols or []
        self.calls: list[tuple] = []

    async def candles(self, tenant_id, symbol, interval, from_ms, to_ms):
        self.calls.append((tenant_id, symbol, interval, from_ms, to_ms))
        return [c for c in self._candles if from_ms <= c.open_time_ms <= to_ms]

    async def symbols(self, tenant_id):
        return list(self._symbols)


@pytest.fixture
def read_repo() -> FakeReadRepository:
    return FakeReadRepository()
