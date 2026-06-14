"""Command service settings.

We extend the shared base so every service reads the same core variables the
same way, then add the write-side specific ones.
"""

from __future__ import annotations

from cryptoscope_shared.settings import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    service_name: str = "command-service"

    postgres_dsn: str = Field(
        default="postgresql+asyncpg://cryptoscope:cryptoscope@postgres:5432/cryptoscope",
        alias="POSTGRES_DSN",
    )

    redis_addr: str = Field(default="redis:6379", alias="REDIS_ADDR")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    events_topic: str = Field(default="domain.events", alias="KAFKA_TOPIC_EVENTS")

    http_port: int = Field(default=8002, alias="COMMAND_SERVICE_HTTP_PORT")

    @property
    def sqlalchemy_dsn(self) -> str:
        """Normalize a libpq style DSN to the asyncpg driver SQLAlchemy expects."""

        dsn = self.postgres_dsn
        if dsn.startswith("postgres://"):
            dsn = dsn.replace("postgres://", "postgresql+asyncpg://", 1)
        elif dsn.startswith("postgresql://"):
            dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
        return dsn.split("?", 1)[0]
