"""
Alembic migration environment configuration for LegalDrishti AI.

This module is executed whenever Alembic migration commands are run.
It connects Alembic to our application's:
1. Application settings (reading DATABASE_URL safely from .env).
2. Base.metadata (allowing Alembic to autogenerate migrations from our ORM models).
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import application settings and ORM Base metadata
from app.core.config import get_settings
from app.core.database import Base

# Alembic Config object: provides access to the values in alembic.ini
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 1. Load application settings safely
settings = get_settings()

# 2. Inject DATABASE_URL into Alembic config dynamically (avoids hardcoding passwords in alembic.ini)
config.set_main_option("sqlalchemy.url", settings.database_url)

# 3. Set target_metadata to Base.metadata so Alembic can detect all tables/models automatically
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Generates raw SQL scripts without requiring an active database connection.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Helper function to run migrations within an active database connection.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode using an asynchronous engine.
    Creates an async engine, connects to the database, and executes migrations.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Entry point for online migrations.
    Starts the asyncio event loop to run async migrations.
    """
    asyncio.run(run_async_migrations())


# Determine whether Alembic is running offline or online
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
