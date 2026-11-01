"""Environment backed settings shared by the Python services.

We read configuration once at startup with pydantic-settings and pass the
resulting object explicitly. Reading os.environ from deep in the code hides
dependencies and makes tests harder.
"""

from __future__ import annotations

import os
import ssl
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic import SecretStr
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
        protocol = self.kafka_security_protocol.strip().upper()
        mechanism = self.kafka_sasl_mechanism.strip().upper()
        if production:
            if protocol != "SASL_SSL":
                raise ValueError("KAFKA_SECURITY_PROTOCOL must be SASL_SSL in production")
            for alias in ("KAFKA_SASL_USERNAME", "KAFKA_SASL_PASSWORD"):
                if not os.getenv(f"{alias}_FILE", "").strip():
                    raise ValueError(f"{alias}_FILE is required in production")
        if protocol == "SASL_SSL":
            if not self.kafka_sasl_username.strip() or not self.kafka_sasl_password.get_secret_value():
                raise ValueError("Kafka SASL username and password are required for SASL_SSL")
            if mechanism not in {"SCRAM-SHA-256", "SCRAM-SHA-512"}:
                raise ValueError("KAFKA_SASL_MECHANISM must be SCRAM-SHA-256 or SCRAM-SHA-512")

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
    kafka_security_protocol: str = Field(default="PLAINTEXT", alias="KAFKA_SECURITY_PROTOCOL")
    kafka_sasl_mechanism: str = Field(default="SCRAM-SHA-512", alias="KAFKA_SASL_MECHANISM")
    kafka_sasl_username: str = Field(default="", alias="KAFKA_SASL_USERNAME")
    kafka_sasl_password: SecretStr = Field(default=SecretStr(""), alias="KAFKA_SASL_PASSWORD")
    kafka_tls_ca_file: str = Field(default="", alias="KAFKA_TLS_CA_FILE")

    @property
    def kafka_broker_list(self) -> list[str]:
        return [b.strip() for b in self.kafka_brokers.split(",") if b.strip()]

    @property
    def kafka_client_options(self) -> dict[str, Any]:
        """Return verified TLS/SASL options for aiokafka constructors."""
        protocol = self.kafka_security_protocol.strip().upper()
        mechanism = self.kafka_sasl_mechanism.strip().upper()
        if protocol == "PLAINTEXT":
            return {"security_protocol": "PLAINTEXT"}
        if protocol != "SASL_SSL":
            raise ValueError("KAFKA_SECURITY_PROTOCOL must be PLAINTEXT or SASL_SSL")
        context = ssl.create_default_context()
        if self.kafka_tls_ca_file:
            context.load_verify_locations(cafile=self.kafka_tls_ca_file)
        return {
            "security_protocol": "SASL_SSL",
            "sasl_mechanism": mechanism,
            "sasl_plain_username": self.kafka_sasl_username,
            "sasl_plain_password": self.kafka_sasl_password.get_secret_value(),
            "ssl_context": context,
        }
