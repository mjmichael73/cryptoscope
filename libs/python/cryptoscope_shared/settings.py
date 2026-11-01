"""Environment backed settings shared by the Python services.

We read configuration once at startup with pydantic-settings and pass the
resulting object explicitly. Reading os.environ from deep in the code hides
dependencies and makes tests harder.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    """Settings common to every Python service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def __init__(self, **values: Any) -> None:
        # Allow Vault Agent and orchestrator secret volumes to supply a value
        # via <ENV_NAME>_FILE. Explicit constructor values retain precedence.
        production = os.getenv("CRYPTOSCOPE_ENV", "").strip().lower() == "production"
        for name, field in type(self).model_fields.items():
            alias = field.validation_alias or field.alias or name
            if not isinstance(alias, str):
                continue
            path = os.getenv(f"{alias}_FILE")
            if production and alias in {
                "POSTGRES_DSN",
                "CLICKHOUSE_USER",
                "CLICKHOUSE_PASSWORD",
                "MONGO_URI",
            } and not path:
                raise ValueError(f"{alias}_FILE is required in production")
            if name in values or alias in values:
                continue
            if path:
                try:
                    secret = Path(path).read_text(encoding="utf-8").rstrip("\r\n")
                except OSError as exc:
                    raise ValueError(f"could not read secret file for {alias}") from exc
                if not secret:
                    raise ValueError(f"secret file for {alias} is empty")
                values[alias] = secret
        super().__init__(**values)

    environment: str = Field(default="local", alias="CRYPTOSCOPE_ENV")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    otel_endpoint: str = Field(
        default="http://otel-collector:4317", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_namespace: str = Field(default="cryptoscope", alias="OTEL_SERVICE_NAMESPACE")

    kafka_brokers: str = Field(default="kafka:9092", alias="KAFKA_BROKERS")
    kafka_consumer_group: str = Field(
        default="cryptoscope", alias="KAFKA_CONSUMER_GROUP"
    )

    @property
    def kafka_broker_list(self) -> list[str]:
        return [b.strip() for b in self.kafka_brokers.split(",") if b.strip()]
