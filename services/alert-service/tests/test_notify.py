"""Tests for the notification channels and dispatcher."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.infra.notify import (
    EmailChannel,
    NotificationChannel,
    NotificationDispatcher,
    SlackWebhookChannel,
    TriggerPayload,
    WebhookChannel,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trigger(**overrides: Any) -> TriggerPayload:
    defaults = {
        "trigger_id": "trg-1",
        "tenant_id": "tenant-1",
        "rule_id": "rule-1",
        "symbol": "BTCUSDT",
        "comparator": "gt",
        "threshold": 50000.0,
        "current_value": 51000.0,
        "triggered_at": "2026-01-01T00:00:00Z",
    }
    defaults.update(overrides)
    return TriggerPayload(**defaults)


class _RecordingHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that records incoming requests."""

    requests: list[dict[str, Any]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        auth = self.headers.get("Authorization", "")
        self.requests.append({
            "path": self.path,
            "body": body.decode(),
            "auth": auth,
        })
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, format: str, *args: Any) -> None:
        pass  # silence


@pytest.fixture(autouse=True)
def _reset_recording() -> None:
    _RecordingHandler.requests = []
    yield


def _start_server() -> tuple[HTTPServer, Thread]:
    server = HTTPServer(("127.0.0.1", 0), _RecordingHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


# ---------------------------------------------------------------------------
# TriggerPayload
# ---------------------------------------------------------------------------

class TestTriggerPayload:
    def test_fields(self) -> None:
        tp = _make_trigger(trigger_id="t-99", symbol="ETHUSDT", threshold=2000.0)
        assert tp.trigger_id == "t-99"
        assert tp.symbol == "ETHUSDT"
        assert tp.threshold == 2000.0

    def test_equality(self) -> None:
        a = _make_trigger(trigger_id="x")
        b = _make_trigger(trigger_id="x")
        assert a == b


# ---------------------------------------------------------------------------
# EmailChannel
# ---------------------------------------------------------------------------

class TestEmailChannel:
    @patch("app.infra.notify.smtplib.SMTP")
    def test_send_success(self, mock_smtp_cls: MagicMock) -> None:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        ch = EmailChannel(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="user",
            password="pass",
            from_addr="alert@test.com",
            to_addrs=["ops@test.com"],
        )
        result = ch.send(_make_trigger())

        assert result is True
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user", "pass")
        mock_smtp.sendmail.assert_called_once()

        # Verify the sent email contains the symbol and threshold.
        call_args = mock_smtp.sendmail.call_args
        body = call_args[0][2]  # third positional arg is the message string
        assert "BTCUSDT" in body
        assert "50000" in body

    @patch("app.infra.notify.smtplib.SMTP")
    def test_send_failure_returns_false(self, mock_smtp_cls: MagicMock) -> None:
        mock_smtp_cls.return_value.__enter__ = MagicMock(
            side_effect=ConnectionRefusedError("refused")
        )

        ch = EmailChannel(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="",
            password="",
            from_addr="alert@test.com",
            to_addrs=["ops@test.com"],
        )
        result = ch.send(_make_trigger())
        assert result is False

    @patch("app.infra.notify.smtplib.SMTP")
    def test_no_login_when_no_username(self, mock_smtp_cls: MagicMock) -> None:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        ch = EmailChannel(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="",
            password="",
            from_addr="alert@test.com",
            to_addrs=["ops@test.com"],
        )
        ch.send(_make_trigger())
        mock_smtp.login.assert_not_called()

    @patch("app.infra.notify.smtplib.SMTP")
    def test_multiple_recipients(self, mock_smtp_cls: MagicMock) -> None:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        ch = EmailChannel(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="",
            password="",
            from_addr="alert@test.com",
            to_addrs=["a@test.com", "b@test.com"],
        )
        ch.send(_make_trigger())
        call_args = mock_smtp.sendmail.call_args
        to_addrs = call_args[0][1]
        assert to_addrs == ["a@test.com", "b@test.com"]


# ---------------------------------------------------------------------------
# SlackWebhookChannel
# ---------------------------------------------------------------------------

class TestSlackWebhookChannel:
    def test_send_posts_to_webhook(self) -> None:
        server, _ = _start_server()
        try:
            host, port = server.server_address
            ch = SlackWebhookChannel(f"http://{host}:{port}/hook")
            result = ch.send(_make_trigger(comparator="gt"))
            assert result is True
            assert len(_RecordingHandler.requests) == 1
            body = json.loads(_RecordingHandler.requests[0]["body"])
            assert "attachments" in body
            assert body["attachments"][0]["color"] == "#ef4444"
        finally:
            server.shutdown()

    def test_send_below_uses_green_color(self) -> None:
        server, _ = _start_server()
        try:
            host, port = server.server_address
            ch = SlackWebhookChannel(f"http://{host}:{port}/hook")
            ch.send(_make_trigger(comparator="lt"))
            body = json.loads(_RecordingHandler.requests[0]["body"])
            assert body["attachments"][0]["color"] == "#22c55e"
        finally:
            server.shutdown()

    def test_send_failure_returns_false(self) -> None:
        ch = SlackWebhookChannel("http://127.0.0.1:1/unreachable")
        result = ch.send(_make_trigger())
        assert result is False

    def test_payload_contains_symbol_and_value(self) -> None:
        server, _ = _start_server()
        try:
            host, port = server.server_address
            ch = SlackWebhookChannel(f"http://{host}:{port}/hook")
            ch.send(_make_trigger(symbol="ETHUSDT", threshold=2000.0, current_value=2100.0))
            body = json.loads(_RecordingHandler.requests[0]["body"])
            fields_text = json.dumps(body)
            assert "ETHUSDT" in fields_text
            assert "2000" in fields_text
            assert "2100" in fields_text
        finally:
            server.shutdown()


# ---------------------------------------------------------------------------
# WebhookChannel
# ---------------------------------------------------------------------------

class TestWebhookChannel:
    def test_send_posts_json_payload(self) -> None:
        server, _ = _start_server()
        try:
            host, port = server.server_address
            ch = WebhookChannel(f"http://{host}:{port}/webhook")
            result = ch.send(_make_trigger(trigger_id="wh-42", symbol="SOLUSDT"))
            assert result is True
            assert len(_RecordingHandler.requests) == 1
            body = json.loads(_RecordingHandler.requests[0]["body"])
            assert body["trigger_id"] == "wh-42"
            assert body["symbol"] == "SOLUSDT"
        finally:
            server.shutdown()

    def test_send_includes_custom_auth_header(self) -> None:
        server, _ = _start_server()
        try:
            host, port = server.server_address
            ch = WebhookChannel(
                f"http://{host}:{port}/webhook",
                headers={"Authorization": "Bearer tok123"},
            )
            ch.send(_make_trigger())
            auth = _RecordingHandler.requests[0]["auth"]
            assert auth == "Bearer tok123"
        finally:
            server.shutdown()

    def test_send_failure_returns_false(self) -> None:
        ch = WebhookChannel("http://127.0.0.1:1/unreachable")
        result = ch.send(_make_trigger())
        assert result is False

    def test_payload_all_fields(self) -> None:
        server, _ = _start_server()
        try:
            host, port = server.server_address
            ch = WebhookChannel(f"http://{host}:{port}/webhook")
            ch.send(_make_trigger())
            body = json.loads(_RecordingHandler.requests[0]["body"])
            expected_keys = {
                "trigger_id", "tenant_id", "rule_id", "symbol",
                "comparator", "threshold", "current_value", "triggered_at",
            }
            assert expected_keys == set(body.keys())
        finally:
            server.shutdown()


# ---------------------------------------------------------------------------
# NotificationDispatcher
# ---------------------------------------------------------------------------

class TestNotificationDispatcher:
    def test_empty_dispatcher_returns_empty_results(self) -> None:
        d = NotificationDispatcher()
        results = d.dispatch(_make_trigger())
        assert results == {}

    def test_dispatch_calls_all_channels(self) -> None:
        ch1 = MagicMock(spec=NotificationChannel)
        ch1.send.return_value = True
        ch2 = MagicMock(spec=NotificationChannel)
        ch2.send.return_value = True

        d = NotificationDispatcher([ch1, ch2])
        results = d.dispatch(_make_trigger())

        ch1.send.assert_called_once()
        ch2.send.assert_called_once()
        assert results == {"MagicMock": True, "MagicMock": True}

    def test_dispatch_continues_after_channel_failure(self) -> None:
        ch1 = MagicMock(spec=NotificationChannel)
        ch1.send.return_value = False
        ch2 = MagicMock(spec=NotificationChannel)
        ch2.send.return_value = True

        d = NotificationDispatcher([ch1, ch2])
        results = d.dispatch(_make_trigger())

        assert ch1.send.called
        assert ch2.send.called

    def test_dispatch_catches_exceptions(self) -> None:
        ch = MagicMock(spec=NotificationChannel)
        ch.send.side_effect = RuntimeError("boom")

        d = NotificationDispatcher([ch])
        results = d.dispatch(_make_trigger())

        assert results[type(ch).__name__] is False

    def test_add_channel(self) -> None:
        d = NotificationDispatcher()
        ch = MagicMock(spec=NotificationChannel)
        ch.send.return_value = True
        d.add_channel(ch)
        assert len(d._channels) == 1

    def test_dispatch_with_real_channels(self) -> None:
        server, _ = _start_server()
        try:
            host, port = server.server_address
            d = NotificationDispatcher([
                WebhookChannel(f"http://{host}:{port}/a"),
                SlackWebhookChannel(f"http://{host}:{port}/b"),
            ])
            results = d.dispatch(_make_trigger())
            assert len(results) == 2
            assert all(v is True for v in results.values())
            assert len(_RecordingHandler.requests) == 2
        finally:
            server.shutdown()
