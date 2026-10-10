from __future__ import annotations

from datetime import date, timedelta

from aiogram.enums import ChatMemberStatus
from aiogram.types import BotCommandScopeAllChatAdministrators, BotCommandScopeAllGroupChats

from qul_bot.bot.commands import publish_menus
from qul_bot.bot.formatting import (
    MESSAGE_BUDGET,
    render_card,
    render_digest,
    render_task_list,
    source_link,
)
from qul_bot.domain.enums import Priority, TaskStatus
from qul_bot.i18n import Translator
from qul_bot.services.tasks import NewTask, TaskFilter, TaskService
from tests.conftest import World

T = Translator("uz")
TODAY = date(2026, 10, 10)
TELEGRAM_LIMIT = 4096


async def test_digest_fits_one_message_even_when_huge(world: World) -> None:
    service = TaskService(world.session)
    for i in range(60):
        await service.create(
            world.workspace,
            world.dev,
            NewTask(
                title=f"Very long overdue task title number {i} " + "x" * 120,
                due=TODAY,  # not in the past, so creation is allowed ...
                assignee_usernames=["devalisher", "devvalijon"],
            ),
        )
    digest = await service.digest(world.workspace.id, TODAY + timedelta(days=3))  # ... now overdue
    assert len(digest.overdue) == 60
    text = render_digest(T, digest, TODAY, limit=10)
    assert len(text) <= TELEGRAM_LIMIT
    assert len(text) <= MESSAGE_BUDGET
    assert "yana" in text  # says that more exist


async def test_list_page_fits_one_message_with_long_names(world: World) -> None:
    service = TaskService(world.session)
    world.dev.first_name = "N" * 64
    world.dev2.first_name = "M" * 64
    for _ in range(15):
        await service.create(
            world.workspace,
            world.dev,
            NewTask(
                title="t" * 200,
                assignee_usernames=["devalisher", "devvalijon", "adminuser", "reviewer1"],
                priority=Priority.HIGH,
            ),
        )
    page = await service.list_tasks(TaskFilter(workspace_id=world.workspace.id), 0, 15)
    text = render_task_list(T, page, "Title", TODAY)
    assert len(text) <= TELEGRAM_LIMIT
    assert "+2" in text  # four assignees collapse to two names plus a counter


async def test_card_escapes_html_everywhere(world: World) -> None:
    world.dev.first_name = "<i>Evil</i>"
    task = await TaskService(world.session).create(
        world.workspace,
        world.dev,
        NewTask(title="<b>x</b>", description="<a href='x'>y</a>", assignee_usernames=[]),
    )
    card = render_card(T, task, TODAY)
    assert "<b>x</b>" not in card
    assert "&lt;b&gt;x&lt;/b&gt;" in card
    assert "<i>Evil</i>" not in card
    assert "&lt;a href='x'&gt;" in card


async def test_overdue_marker_only_for_open_tasks(world: World) -> None:
    service = TaskService(world.session)
    task = await service.create(
        world.workspace, world.dev, NewTask(title="late", due=TODAY, assignee_usernames=[])
    )
    later = TODAY + timedelta(days=2)
    assert "muddati o'tgan" in render_card(T, task, later)
    task.status = TaskStatus.DONE
    assert "muddati o'tgan" not in render_card(T, task, later)


def test_source_links() -> None:
    assert source_link(-1001234567890, 77) == "https://t.me/c/1234567890/77"
    assert source_link(-12345, 77) is None  # basic groups have no message links
    assert source_link(None, 5) is None
    assert source_link(-1001234567890, None) is None


async def test_menus_are_published_for_each_scope() -> None:
    from aiogram import Bot

    from tests.fake_telegram import FakeSession

    session = FakeSession()
    bot = Bot("123456:TEST", session=session)
    await publish_menus(bot, T)
    scopes = [type(getattr(c, "scope", None)) for c in session.calls]
    assert BotCommandScopeAllGroupChats in scopes
    assert BotCommandScopeAllChatAdministrators in scopes
    admin_call = next(
        c
        for c in session.calls
        if isinstance(getattr(c, "scope", None), BotCommandScopeAllChatAdministrators)
    )
    names = [command.command for command in admin_call.commands]  # type: ignore[attr-defined]
    assert {"task", "approve", "role"} <= set(names)
    assert ChatMemberStatus.CREATOR  # (imported to keep the enum in view of readers)
