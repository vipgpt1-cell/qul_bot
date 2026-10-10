"""The migration history must produce exactly the schema the models describe."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from qul_bot.db.base import Base
from qul_bot.db.session import create_engine
from tests.conftest import database_url

ROOT = Path(__file__).parents[1]


def alembic_config(url: str) -> Config:
    config = Config()  # no ini file: keeps pytest's logging untouched
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    return config


async def test_migrations_match_models_and_are_reversible(tmp_path: Path) -> None:
    url = database_url(tmp_path)
    engine = create_engine(url)
    async with engine.begin() as conn:  # start from an empty database
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))

    config = alembic_config(url)
    # Alembic runs its own event loop, so it must not run inside ours.
    await asyncio.to_thread(command.upgrade, config, "head")

    async with engine.connect() as conn:
        diff = await conn.run_sync(
            lambda sync_conn: compare_metadata(
                MigrationContext.configure(sync_conn, opts={"compare_type": True}),
                Base.metadata,
            )
        )
    assert diff == [], f"models and migrations disagree: {diff}"

    await asyncio.to_thread(command.downgrade, config, "base")
    async with engine.connect() as conn:
        remaining = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
    assert remaining <= {"alembic_version"}
    await engine.dispose()
