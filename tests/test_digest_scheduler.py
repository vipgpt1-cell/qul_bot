from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage
from sqlalchemy.ext.asyncio import AsyncEngine

from qul_bot.bot import scheduler
from qul_bot.bot.scheduler import run_scheduler, send_due_digests
from qul_bot.db.models import Workspace
from qul_bot.db.session import create_sessionmaker
from qul_bot.services.digests import DigestService
from qul_bot.services.tasks import NewTask, TaskService
from tests.conftest import CHAT_ID, World
from tests.fake_telegram import FakeSession

# 04:00 UTC is 09:00 in Tashkent (UTC+5). 2026-10-13 is a Tuesday.
TUE_9AM = datetime(2026, 10, 13, 4, 0, tzinfo=UTC)


def utc(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC)


async def claim(world: World, now: datetime) -> list[int]:
    due = await DigestService(world.session).claim_due(now)
    return [w.id for w in due]


# ---- which workspaces are due ---------------------------------------------------------


async def test_due_at_the_local_time_and_claimed_once(world: World) -> None:
    assert await claim(world, utc(13, 3, 59)) == []  # 08:59 in Tashkent
    assert await claim(world, TUE_9AM) == [world.workspace.id]
    assert await claim(world, TUE_9AM) == []  # already claimed today
    assert await claim(world, utc(13, 5, 0)) == []
    assert world.workspace.last_digest_on == date(2026, 10, 13)
    assert await claim(world, utc(14, 4, 0)) == [world.workspace.id]  # next working day


async def test_not_on_weekends_or_after_the_grace_window(world: World) -> None:
    assert await claim(world, utc(10, 4, 0)) == []  # Saturday
    assert await claim(world, utc(11, 4, 0)) == []  # Sunday
    assert await claim(world, utc(13, 7, 1)) == []  # 12:01 local: too late for a morning digest
    assert await claim(world, utc(13, 6, 59)) == [world.workspace.id]  # 11:59 local: still fine


async def test_respects_workspace_timezone_and_time(world: World) -> None:
    world.workspace.timezone = "UTC"
    assert await claim(world, utc(13, 4, 0)) == []  # 04:00 UTC is early in UTC
    world.workspace.digest_time = "04:00"
    assert await claim(world, utc(13, 4, 0)) == [world.workspace.id]


async def test_disabled_workspaces_are_skipped(world: World) -> None:
    world.workspace.digest_enabled = False
    assert await claim(world, TUE_9AM) == []


async def test_naive_time_is_a_programming_error(world: World) -> None:
    with pytest.raises(ValueError):
        await DigestService(world.session).claim_due(datetime(2026, 10, 13, 4, 0))


# ---- posting --------------------------------------------------------------------------


@pytest.fixture
def fake_bot() -> tuple[Bot, FakeSession]:
    session = FakeSession()
    return Bot("123456:TEST", session=session), session


async def make_task(world: World) -> None:
    await TaskService(world.session).create(
        world.workspace, world.dev, NewTask(title="Unowned work")
    )
    await world.session.commit()


async def test_digest_is_posted_once_and_only_when_there_is_something(
    world: World, engine: AsyncEngine, fake_bot: tuple[Bot, FakeSession]
) -> None:
    bot, telegram = fake_bot
    sessionmaker = create_sessionmaker(engine)
    await make_task(world)

    assert await send_due_digests(bot, sessionmaker, TUE_9AM) == 1
    [message] = telegram.sent()
    assert message.chat_id == CHAT_ID
    assert "Xulosa" in message.text
    assert "Unowned work" in message.text

    assert await send_due_digests(bot, sessionmaker, TUE_9AM) == 0  # never twice a day
    assert len(telegram.sent()) == 1


async def test_nothing_to_report_posts_nothing_but_uses_up_the_day(
    world: World, engine: AsyncEngine, fake_bot: tuple[Bot, FakeSession]
) -> None:
    bot, telegram = fake_bot
    await world.session.commit()
    assert await send_due_digests(bot, create_sessionmaker(engine), TUE_9AM) == 0
    assert telegram.sent() == []
    async with create_sessionmaker(engine)() as check:
        stored = await check.get(Workspace, world.workspace.id)
        assert stored is not None
        assert stored.last_digest_on == date(2026, 10, 13)


async def test_a_failed_send_is_logged_and_never_retried_into_duplicates(
    world: World,
    engine: AsyncEngine,
    fake_bot: tuple[Bot, FakeSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot, telegram = fake_bot
    await make_task(world)

    async def refuse(*args: object, **kwargs: object) -> object:
        raise TelegramBadRequest(
            method=SendMessage(chat_id=CHAT_ID, text="x"), message="chat not found"
        )

    monkeypatch.setattr(telegram, "make_request", refuse)
    assert await send_due_digests(bot, create_sessionmaker(engine), TUE_9AM) == 0  # no crash

    monkeypatch.undo()
    assert await send_due_digests(bot, create_sessionmaker(engine), TUE_9AM) == 0  # at most once


async def test_loop_survives_a_failing_tick_and_stops_when_cancelled(
    engine: AsyncEngine,
    fake_bot: tuple[Bot, FakeSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot, _ = fake_bot
    calls = 0

    async def flaky(*args: object, **kwargs: object) -> int:
        nonlocal calls
        calls += 1
        raise RuntimeError("boom")

    monkeypatch.setattr(scheduler, "send_due_digests", flaky)
    task = asyncio.create_task(run_scheduler(bot, create_sessionmaker(engine), interval=0.01))
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert calls >= 2  # kept going after the first failure


async def test_workspace_without_chat_is_never_due(world: World, tmp_path: Path) -> None:
    world.workspace.telegram_chat_id = None
    assert await claim(world, TUE_9AM) == []
