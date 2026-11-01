"""Notification dispatcher for alert triggers.

Dispatches alert trigger data through configured channels. Each channel
implements a simple ``send`` method. The dispatcher tries every enabled
channel and logs failures without blocking the alert engine.
"""

from __future__ import annotations

import json
import logging
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass
class TriggerPayload:
    """Normalized alert trigger data sent to every channel."""

    trigger_id: str
    tenant_id: str
    rule_id: str
    symbol: str
    comparator: str
    threshold: float
    current_value: float
    triggered_at: str


class NotificationChannel(ABC):
    """Base class for notification dispatchers."""

    @abstractmethod
    def send(self, trigger: TriggerPayload) -> bool:
        """Send the notification. Returns True on success."""
        ...


class EmailChannel(NotificationChannel):
    """Sends alerts via SMTP."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: list[str],
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    def send(self, trigger: TriggerPayload) -> bool:
        subject = f"[cryptoscope] Alert: {trigger.symbol} {trigger.comparator} {trigger.threshold}"
        body = (
            f"Alert triggered for {trigger.symbol}\n\n"
            f"  Comparator: {trigger.comparator}\n"
            f"  Threshold:  {trigger.threshold}\n"
            f"  Current:    {trigger.current_value}\n"
            f"  Triggered:  {trigger.triggered_at}\n"
            f"  Rule ID:    {trigger.rule_id}\n"
            f"  Trigger ID: {trigger.trigger_id}\n"
        )
        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as s:
                s.starttls()
                if self.username:
                    s.login(self.username, self.password)
                s.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            return True
        except Exception:
            logging.exception("email send failed")
            return False


class SlackWebhookChannel(NotificationChannel):
    """Sends alerts to a Slack incoming webhook."""

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def send(self, trigger: TriggerPayload) -> bool:
        color = "#ef4444" if "above" in trigger.comparator or trigger.comparator in ("gt", "gte") else "#22c55e"
        payload = {
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"⚠️ Alert: {trigger.symbol}",
                            },
                        },
                        {
                            "type": "section",
                            "fields": [
                                {"type": "mrkdwn", "text": f"*Comparator:*\n{trigger.comparator}"},
                                {"type": "mrkdwn", "text": f"*Threshold:*\n{trigger.threshold}"},
                                {"type": "mrkdwn", "text": f"*Current Value:*\n{trigger.current_value}"},
                                {"type": "mrkdwn", "text": f"*Triggered:*\n{trigger.triggered_at}"},
                            ],
                        },
                    ],
                }
            ]
        }
        return self._post(payload)

    def _post(self, payload: dict[str, Any]) -> bool:
        data = json.dumps(payload).encode()
        req = Request(self.webhook_url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=10) as resp:
                return 200 <= resp.status < 300
        except (URLError, OSError):
            logging.exception("slack webhook send failed")
            return False


class WebhookChannel(NotificationChannel):
    """POSTs trigger data to a generic webhook URL."""

    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self.url = url
        self.headers = headers or {}

    def send(self, trigger: TriggerPayload) -> bool:
        payload = {
            "trigger_id": trigger.trigger_id,
            "tenant_id": trigger.tenant_id,
            "rule_id": trigger.rule_id,
            "symbol": trigger.symbol,
            "comparator": trigger.comparator,
            "threshold": trigger.threshold,
            "current_value": trigger.current_value,
            "triggered_at": trigger.triggered_at,
        }
        data = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json", **self.headers}
        req = Request(self.url, data=data, headers=headers)
        try:
            with urlopen(req, timeout=10) as resp:
                return 200 <= resp.status < 300
        except (URLError, OSError):
            logging.exception("webhook send failed")
            return False


class NotificationDispatcher:
    """Dispatches a trigger to all configured channels."""

    def __init__(self, channels: list[NotificationChannel] | None = None) -> None:
        self._channels: list[NotificationChannel] = channels or []

    def add_channel(self, channel: NotificationChannel) -> None:
        self._channels.append(channel)

    def dispatch(self, trigger: TriggerPayload) -> dict[str, bool]:
        """Send to every channel. Returns a map of channel type to success flag."""
        results: dict[str, bool] = {}
        for ch in self._channels:
            name = type(ch).__name__
            try:
                results[name] = ch.send(trigger)
            except Exception:
                logging.exception("notification channel %s failed", name)
                results[name] = False
        return results
