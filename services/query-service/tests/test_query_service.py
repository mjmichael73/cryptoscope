"""Unit tests for the read-side use cases."""

from __future__ import annotations

import pytest

from app.domain.errors import ValidationError
from app.domain.models import SymbolSummary
from app.domain.service import QueryService
from tests.conftest import TENANT_ID, FakeReadRepository, make_candles


async def test_get_candles_uppercases_symbol_and_scopes_tenant():
    repo = FakeReadRepository(candles=make_candles([1, 2, 3]))
    service = QueryService(repo)

    candles = await service.get_candles(TENANT_ID, "btcusdt", "1m", 0, 10**12)

    assert len(candles) == 3
    assert repo.calls[0][0] == TENANT_ID
    assert repo.calls[0][1] == "BTCUSDT"


async def test_get_candles_rejects_unknown_interval():
    service = QueryService(FakeReadRepository())
    with pytest.raises(ValidationError):
        await service.get_candles(TENANT_ID, "BTCUSDT", "3m", 0, 1)


async def test_get_candles_rejects_reversed_range():
    service = QueryService(FakeReadRepository())
    with pytest.raises(ValidationError):
        await service.get_candles(TENANT_ID, "BTCUSDT", "1m", 10, 5)


async def test_get_indicator_folds_candles():
    repo = FakeReadRepository(candles=make_candles([1, 2, 3, 4, 5]))
    service = QueryService(repo)

    points = await service.get_indicator(TENANT_ID, "BTCUSDT", "1m", "sma", 3, 0, 10**12)
    assert [p.value for p in points] == [2.0, 3.0, 4.0]


async def test_list_symbols_passes_through():
    repo = FakeReadRepository(symbols=["BTCUSDT", "ETHUSDT"])
    service = QueryService(repo)

    assert await service.list_symbols(TENANT_ID) == ["BTCUSDT", "ETHUSDT"]


def _summary(symbol: str) -> SymbolSummary:
    return SymbolSummary(
        symbol=symbol,
        first_open_time_ms=1_000_000,
        last_open_time_ms=2_000_000,
        candle_count=10,
        intervals=["1m", "5m"],
    )


async def test_search_symbols_returns_summaries():
    repo = FakeReadRepository(summaries=[_summary("BTCUSDT")])
    service = QueryService(repo)

    result = await service.search_symbols(TENANT_ID, "BTC", 50)

    assert result == [_summary("BTCUSDT")]
    assert repo.search_calls[0] == (TENANT_ID, "BTC", 50)


async def test_search_symbols_uppercases_and_strips_query():
    repo = FakeReadRepository()
    service = QueryService(repo)

    await service.search_symbols(TENANT_ID, "  eth ", 10)

    assert repo.search_calls[0] == (TENANT_ID, "ETH", 10)


async def test_search_symbols_rejects_limit_below_one():
    service = QueryService(FakeReadRepository())
    with pytest.raises(ValidationError):
        await service.search_symbols(TENANT_ID, "", 0)


async def test_search_symbols_rejects_limit_above_200():
    service = QueryService(FakeReadRepository())
    with pytest.raises(ValidationError):
        await service.search_symbols(TENANT_ID, "", 201)


async def test_search_symbols_rejects_overlong_query():
    service = QueryService(FakeReadRepository())
    with pytest.raises(ValidationError):
        await service.search_symbols(TENANT_ID, "A" * 101, 50)
