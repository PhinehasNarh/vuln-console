"""Alembic environment: async engine, all context metadata."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from vulnconsole.contexts.identity.domain import models as identity_models
from vulnconsole.contexts.ingestion.domain import models as ingestion_models
from vulnconsole.contexts.normalization.domain import models as normalization_models
from vulnconsole.contexts.notifications.domain import models as notifications_models
from vulnconsole.shared.config import get_settings
from vulnconsole.shared.db import Base

# Importing the model modules registers every table on Base.metadata so that
# migrations and autogenerate see the full schema. Referenced here so the
# imports are not flagged as unused.
_REGISTERED_MODELS = (
    identity_models,
    ingestion_models,
    normalization_models,
    notifications_models,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata, include_schemas=True
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
