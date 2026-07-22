"""SQLAlchemy models for the write side.

Every tenant-owned table carries a tenant_id so a single shared database can
host many tenants with row level scoping. Indexes are chosen for the access
patterns the API actually uses.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class UUIDType(TypeDecorator):
    """UUID on Postgres, a plain string elsewhere.

    This keeps the production schema on native uuid columns while letting the
    unit tests run against SQLite without special casing the models.
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=False))
        return dialect.type_descriptor(String(36))


class StringArray(TypeDecorator):
    """String array on Postgres, a JSON encoded string elsewhere."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql" or value is None:
            return value
        import json

        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql" or value is None:
            return value
        import json

        return json.loads(value)


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(UUIDType(), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[str] = mapped_column(UUIDType(), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        UUIDType(), ForeignKey("tenants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    symbols: Mapped[list[str]] = mapped_column(StringArray(), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_watchlist_tenant_name"),
        Index("ix_watchlist_tenant", "tenant_id"),
    )


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(UUIDType(), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        UUIDType(), ForeignKey("tenants.id"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    comparator: Mapped[str] = mapped_column(String(8), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    __table_args__ = (
        Index("ix_alert_rule_tenant_symbol", "tenant_id", "symbol"),
    )


class ProcessedCommand(Base):
    """Idempotency ledger.

    A command carries a client supplied key. We record the key together with the
    resource it produced, so a retry with the same key returns the original
    result instead of creating a duplicate.
    """

    __tablename__ = "processed_commands"

    tenant_id: Mapped[str] = mapped_column(UUIDType(), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    resource_id: Mapped[str] = mapped_column(UUIDType(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
