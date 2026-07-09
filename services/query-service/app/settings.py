"""Query service settings."""

from __future__ import annotations

from cryptoscope_shared.settings import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    service_name: str = "query-service"

    clickhouse_host: str = Field(default="clickhouse", alias="CLICKHOUSE_HOST")
    clickhouse_http_port: int = Field(default=8123, alias="CLICKHOUSE_HTTP_PORT")
    clickhouse_db: str = Field(default="cryptoscope", alias="CLICKHOUSE_DB")
    clickhouse_user: str = Field(default="cryptoscope", alias="CLICKHOUSE_USER")
    clickhouse_password: str = Field(default="cryptoscope", alias="CLICKHOUSE_PASSWORD")

    redis_addr: str = Field(default="redis:6379", alias="REDIS_ADDR")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    http_port: int = Field(default=8001, alias="QUERY_SERVICE_HTTP_PORT")
    grpc_port: int = Field(default=9001, alias="QUERY_SERVICE_GRPC_PORT")

    cache_ttl_seconds: int = Field(default=15, alias="QUERY_CACHE_TTL_SECONDS")
