from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas import (
    CreateAlertRuleRequest,
    CreatedResponse,
    CreateWatchlistRequest,
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
    assert req.interval == "1m"
    assert req.window_seconds is None
    assert req.cooldown_seconds == 300


def test_create_alert_rule_request_accepts_new_comparator_and_window() -> None:
    req = CreateAlertRuleRequest(
        symbol="BTCUSDT", comparator="pct_change_below", threshold=5.0, window_seconds=3600
    )
    assert req.comparator == "pct_change_below"
    assert req.window_seconds == 3600


def test_create_alert_rule_request_rejects_bad_comparator() -> None:
    with pytest.raises(ValidationError):
        CreateAlertRuleRequest(
            symbol="BTCUSDT", comparator="invalid", threshold=100.0
        )


def test_create_alert_rule_request_rejects_window_out_of_range() -> None:
    with pytest.raises(ValidationError):
        CreateAlertRuleRequest(
            symbol="BTCUSDT", comparator="pct_change_below", threshold=5.0, window_seconds=30
        )


def test_create_alert_rule_request_rejects_unsupported_interval() -> None:
    with pytest.raises(ValidationError):
        CreateAlertRuleRequest(
            symbol="BTCUSDT", comparator="above", threshold=100.0, interval="4h"
        )


def test_create_alert_rule_request_rejects_empty_symbol() -> None:
    with pytest.raises(ValidationError):
        CreateAlertRuleRequest(symbol="", comparator="above", threshold=100.0)


def test_created_response() -> None:
    resp = CreatedResponse(id="resource-1")
    assert resp.id == "resource-1"
