from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AlertRuleModel(Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    comparator: Mapped[str] = mapped_column(String(32), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    interval: Mapped[str] = mapped_column(String(8), nullable=False, default="1m")
    window_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AlertTriggerModel(Base):
    __tablename__ = "alert_triggers"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("alert_rules.id"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    comparator: Mapped[str] = mapped_column(String(32), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    interval: Mapped[str] = mapped_column(String(8), nullable=False, default="1m")
    window_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)


def build_engine(dsn: str):
    return create_async_engine(dsn, echo=False, pool_size=5, max_overflow=10)


def build_session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
