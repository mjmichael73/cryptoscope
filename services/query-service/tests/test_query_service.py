"""Unit tests for the read-side use cases."""

from __future__ import annotations

import pytest

from app.domain.errors import ValidationError
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
