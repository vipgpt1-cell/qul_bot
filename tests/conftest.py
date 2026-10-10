from __future__ import annotations

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from qul_bot.db.base import Base
from qul_bot.db.models import User, Workspace
from qul_bot.db.session import create_engine, create_sessionmaker
from qul_bot.domain.enums import Role
from qul_bot.domain.workflow import Actor
from qul_bot.services.users import UserService
from qul_bot.services.workspaces import WorkspaceService

CHAT_ID = -1001234567890


def database_url(tmp_path: Path) -> str:
    """SQLite by default; set TEST_DATABASE_URL=postgresql+asyncpg://... to test Postgres."""
    return os.environ.get("TEST_DATABASE_URL") or f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(database_url(tmp_path))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with create_sessionmaker(engine)() as session:
        yield session


@dataclass
class World:
    """A workspace with one admin, one reviewer and two plain developers."""

    session: AsyncSession
    workspace: Workspace
    admin: User
    reviewer: User
    dev: User
    dev2: User

    @staticmethod
    def actor(user: User, role: Role) -> Actor:
        return Actor(user_id=user.id, role=role)

    @property
    def admin_actor(self) -> Actor:
        return Actor(self.admin.id, Role.ADMIN)

    @property
    def reviewer_actor(self) -> Actor:
        return Actor(self.reviewer.id, Role.REVIEWER)

    @property
    def dev_actor(self) -> Actor:
        return Actor(self.dev.id, Role.MEMBER)

    @property
    def dev2_actor(self) -> Actor:
        return Actor(self.dev2.id, Role.MEMBER)


@pytest.fixture
async def world(session: AsyncSession) -> World:
    users, workspaces = UserService(session), WorkspaceService(session)
    workspace = await workspaces.create(CHAT_ID, "Team", "uz", "Asia/Tashkent")

    async def member(telegram_id: int, username: str, name: str, role: Role) -> User:
        user = await users.upsert_telegram(telegram_id, username, name, None)
        await session.flush()
        await workspaces.add_member(workspace.id, user, role)
        return user

    return World(
        session=session,
        workspace=workspace,
        admin=await member(1, "adminuser", "Admin", Role.ADMIN),
        reviewer=await member(2, "reviewer1", "Reviewer", Role.REVIEWER),
        dev=await member(3, "devalisher", "Alisher", Role.MEMBER),
        dev2=await member(4, "devvalijon", "Valijon", Role.MEMBER),
    )
