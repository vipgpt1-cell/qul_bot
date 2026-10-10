from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

import qul_bot.db.models  # noqa: F401  (registers the tables on Base.metadata)
from qul_bot.config import DatabaseSettings
from qul_bot.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str:
    # Tests (and `alembic -x`) can inject a URL; normally it comes from DATABASE_URL / .env.
    return config.get_main_option("sqlalchemy.url") or DatabaseSettings().database_url


def _render_as_batch(connection: Connection | None) -> bool:
    """SQLite cannot ALTER most things, so generated migrations use batch mode for it.

    `alembic -x batch=0 revision --autogenerate` turns that off (e.g. when targeting Postgres).
    """
    if context.get_x_argument(as_dictionary=True).get("batch") == "0":
        return False
    return connection is not None and connection.dialect.name == "sqlite"


def _configure(connection: Connection | None, url: str | None = None) -> None:
    context.configure(
        connection=connection,
        url=url,
        target_metadata=target_metadata,
        compare_type=True,
        literal_binds=connection is None,
        render_as_batch=_render_as_batch(connection),
    )


def run_migrations_offline() -> None:
    _configure(None, url=_database_url())
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection: Connection) -> None:
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(_database_url(), poolclass=NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
