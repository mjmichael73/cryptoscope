"""Environment backed settings shared by the Python services.

We read configuration once at startup with pydantic-settings and pass the
resulting object explicitly. Reading os.environ from deep in the code hides
dependencies and makes tests harder.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    """Settings common to every Python service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
