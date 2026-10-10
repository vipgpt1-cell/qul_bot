"""Several people typing at once must never produce duplicate task numbers."""

from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from qul_bot.db.session import create_sessionmaker
from qul_bot.services.tasks import NewTask, TaskService
from qul_bot.services.users import UserService
from qul_bot.services.workspaces import WorkspaceService
from tests.conftest import CHAT_ID

WORKERS = 12


async def test_concurrent_creation_yields_unique_gap_free_numbers(
    engine: AsyncEngine, tmp_path: Path
) -> None:
    sessionmaker = create_sessionmaker(engine)
    async with sessionmaker() as setup:
        workspace = await WorkspaceService(setup).create(CHAT_ID, "T", "uz", "Asia/Tashkent")
        user = await UserService(setup).upsert_telegram(1, "someone1", "Some", None)
        await setup.commit()
        workspace_id, user_id = workspace.id, user.id

    async def create_one(i: int) -> int:
        async with sessionmaker() as session:
            workspaces = WorkspaceService(session)
            ws = await session.get(type(workspace), workspace_id)
            reporter = await session.get(type(user), user_id)
            assert ws is not None and reporter is not None
            task = await TaskService(session).create(ws, reporter, NewTask(title=f"task {i}"))
            await session.commit()
            assert workspaces is not None
            return task.number

    numbers = await asyncio.gather(*(create_one(i) for i in range(WORKERS)))
    assert sorted(numbers) == list(range(1, WORKERS + 1))


async def test_concurrent_first_contact_creates_one_user(engine: AsyncEngine) -> None:
    sessionmaker = create_sessionmaker(engine)

    async def hello() -> int:
        async with sessionmaker() as session:
            user = await UserService(session).upsert_telegram(77, "newcomer1", "New", None)
            await session.commit()
            return user.id

    ids = await asyncio.gather(*(hello() for _ in range(6)))
    assert len(set(ids)) == 1
