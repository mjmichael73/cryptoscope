from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas import (
    CreateAlertRuleRequest,
    CreateWatchlistRequest,
    CreatedResponse,
)


def test_create_watchlist_request_valid() -> None:
    req = CreateWatchlistRequest(name="Majors", symbols=["BTCUSDT", "ETHUSDT"])
    assert req.name == "Majors"
    assert len(req.symbols) == 2


def test_create_watchlist_request_default_symbols() -> None:
    req = CreateWatchlistRequest(name="Empty")
    assert req.symbols == []


def test_create_watchlist_request_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        CreateWatchlistRequest(name="", symbols=[])


def test_create_watchlist_request_rejects_long_name() -> None:
    with pytest.raises(ValidationError):
        CreateWatchlistRequest(name="x" * 129, symbols=[])


def test_create_alert_rule_request_valid() -> None:
    req = CreateAlertRuleRequest(
        symbol="BTCUSDT", comparator="above", threshold=50000.0
    )
    assert req.symbol == "BTCUSDT"
    assert req.threshold == 50000.0


def test_create_alert_rule_request_rejects_bad_comparator() -> None:
    with pytest.raises(ValidationError):
        CreateAlertRuleRequest(
            symbol="BTCUSDT", comparator="invalid", threshold=100.0
        )


def test_create_alert_rule_request_rejects_empty_symbol() -> None:
    with pytest.raises(ValidationError):
        CreateAlertRuleRequest(symbol="", comparator="above", threshold=100.0)


def test_created_response() -> None:
    resp = CreatedResponse(id="resource-1")
    assert resp.id == "resource-1"
