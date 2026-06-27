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

    @property
    def sqlalchemy_dsn(self) -> str:
        dsn = self.postgres_dsn
        if dsn.startswith("postgres://"):
            dsn = dsn.replace("postgres://", "postgresql+asyncpg://", 1)
        elif dsn.startswith("postgresql://"):
            dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
        return dsn.split("?", 1)[0]
