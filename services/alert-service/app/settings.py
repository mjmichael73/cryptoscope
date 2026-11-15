from __future__ import annotations

from cryptoscope_shared.settings import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    service_name: str = "alert-service"

    postgres_dsn: str = Field(
        default="postgresql+asyncpg://cryptoscope:cryptoscope@postgres:5432/cryptoscope",
        alias="POSTGRES_DSN",
    )

    events_topic: str = Field(default="domain.events", alias="KAFKA_TOPIC_EVENTS")
    alerts_topic: str = Field(default="alerts.triggers", alias="KAFKA_TOPIC_ALERTS")

    http_port: int = Field(default=8003, alias="ALERT_SERVICE_HTTP_PORT")

    # Notification channels (all optional — empty means notifications disabled)
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="", alias="SMTP_FROM")
    smtp_to: str = Field(default="", alias="SMTP_TO")  # comma-separated

    slack_webhook_url: str = Field(default="", alias="SLACK_WEBHOOK_URL")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")

    # Rolling close history per (symbol, interval) used by crossing, percent
    # change and RSI comparators. 480 closes of 1m candles ≈ 8 hours.
    price_history_maxlen: int = Field(default=480, alias="PRICE_HISTORY_MAXLEN")

    webhook_url: str = Field(default="", alias="ALERT_WEBHOOK_URL")
    webhook_auth_header: str = Field(default="", alias="ALERT_WEBHOOK_AUTH")

    @property
    def sqlalchemy_dsn(self) -> str:
        dsn = self.postgres_dsn
        if dsn.startswith("postgres://"):
            dsn = dsn.replace("postgres://", "postgresql+asyncpg://", 1)
        elif dsn.startswith("postgresql://"):
            dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
        return dsn.split("?", 1)[0]
