from __future__ import annotations

import pytest

from app.api.schemas import CandleOut, IndicatorPointOut, SymbolsOut
from app.domain.errors import ValidationError as DomainValidationError
from app.domain.models import Candle, IndicatorPoint


def test_candle_dataclass() -> None:
    candle = Candle(
        open_time_ms=1700000000000,
        open=49000.0,
        high=51000.0,
        low=48000.0,
        close=50500.0,
        volume=100.5,
    )
    assert candle.close == 50500.0
    assert candle.volume == 100.5


def test_candle_is_frozen() -> None:
    candle = Candle(
        open_time_ms=1, open=1.0, high=1.0, low=1.0, close=1.0, volume=1.0
    )
    with pytest.raises(AttributeError):
        candle.close = 2.0


def test_indicator_point() -> None:
    pt = IndicatorPoint(time_ms=1700000000000, value=50000.0)
    assert pt.time_ms == 1700000000000
    assert pt.value == 50000.0


def test_candle_out_schema() -> None:
    out = CandleOut(
        open_time_ms=1, open=1.0, high=2.0, low=0.5, close=1.5, volume=10.0
    )
    assert out.open_time_ms == 1
    assert out.high == 2.0


def test_indicator_point_out_schema() -> None:
    out = IndicatorPointOut(time_ms=1700000000000, value=50000.0)
    assert out.value == 50000.0


def test_symbols_out_schema() -> None:
    out = SymbolsOut(symbols=["BTCUSDT", "ETHUSDT"])
    assert len(out.symbols) == 2


def test_domain_validation_error() -> None:
    exc = DomainValidationError("invalid interval")
    assert isinstance(exc, ValueError)
    assert str(exc) == "invalid interval"
