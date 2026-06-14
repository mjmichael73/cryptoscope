"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(dsn: str) -> AsyncEngine:
    # pool_pre_ping guards against connections dropped by the database or a
    # proxy between requests, which is common in containerized deployments.
    return create_async_engine(dsn, pool_pre_ping=True, future=True)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
