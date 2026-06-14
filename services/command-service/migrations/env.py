"""Alembic environment for the command service.

Migrations run synchronously with a psycopg style URL. At runtime the service
uses asyncpg, but for migrations a plain sync driver keeps things simple and
avoids an event loop inside Alembic.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.domain.models import Base
from app.settings import Settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_dsn() -> str:
    dsn = Settings().sqlalchemy_dsn
    return dsn.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_dsn(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _sync_dsn()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
