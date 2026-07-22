from __future__ import annotations

from app.domain.commands import CreateAlertRule, CreateWatchlist
from app.domain.errors import ConflictError, ValidationError
from app.domain.events import DomainEvent, alert_rule_created, watchlist_created


def test_create_watchlist_command() -> None:
    cmd = CreateWatchlist(
        tenant_id="tenant-1",
        idempotency_key="key-1",
        name="Majors",
        symbols=["BTCUSDT", "ETHUSDT"],
    )
    assert cmd.tenant_id == "tenant-1"
    assert cmd.name == "Majors"
    assert "BTCUSDT" in cmd.symbols


def test_create_alert_rule_command() -> None:
    cmd = CreateAlertRule(
        tenant_id="tenant-1",
        idempotency_key="rule-1",
        symbol="BTCUSDT",
        comparator="above",
        threshold=50000.0,
    )
    assert cmd.comparator == "above"
    assert cmd.symbol == "BTCUSDT"


def test_validation_error_is_value_error() -> None:
    exc = ValidationError("invalid input")
    assert isinstance(exc, ValueError)
    assert str(exc) == "invalid input"


def test_conflict_error_is_runtime_error() -> None:
    exc = ConflictError("duplicate key")
    assert isinstance(exc, RuntimeError)
    assert str(exc) == "duplicate key"


def test_domain_event_creation() -> None:
    event = DomainEvent(
        name="watchlist.created",
        tenant_id="tenant-1",
        payload={"id": "wl-1"},
    )
    assert event.name == "watchlist.created"
    assert event.tenant_id == "tenant-1"
    assert event.payload["id"] == "wl-1"
    assert event.occurred_at is not None


def test_domain_event_to_message() -> None:
    event = DomainEvent(
        name="watchlist.created",
        tenant_id="tenant-1",
        payload={"id": "wl-1", "symbols": []},
    )
    msg = event.to_message()
    assert msg["name"] == "watchlist.created"
    assert msg["tenant_id"] == "tenant-1"
    assert msg["payload"]["id"] == "wl-1"


def test_watchlist_created_factory() -> None:
    event = watchlist_created("tenant-1", "wl-1", "Majors", ["BTCUSDT"])
    assert event.name == "watchlist.created"
    assert event.payload["symbols"] == ["BTCUSDT"]
    assert event.payload["name"] == "Majors"


def test_alert_rule_created_factory() -> None:
    event = alert_rule_created("tenant-1", "rule-1", "BTCUSDT", "above", 50000.0)
    assert event.name == "alert_rule.created"
    assert event.payload["symbol"] == "BTCUSDT"
    assert event.payload["threshold"] == 50000.0
