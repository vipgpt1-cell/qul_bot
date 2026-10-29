"""/ai end to end, with a scripted model."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from qul_bot.bot.app import create_dispatcher
from qul_bot.config import Settings
from qul_bot.db.session import create_sessionmaker
from qul_bot.errors import AppError
from tests.conftest import database_url
from tests.fake_ai import FakeAIClient
from tests.fake_telegram import GROUP_ID, Harness
from tests.test_bot_flow import ADMIN, ALI, VALI, build_harness, introduce

PROPOSAL = json.dumps({
    "summary": "Login va to'lov muhokamasi",
    "tasks": [
        {"title": "Login xatosini tuzatish", "description": "iOS da", "priority": "high",
         "assignee": "devalisher", "due": "ertaga"},
        {"title": "To'lov <sahifasi>", "description": None, "priority": None,
         "assignee": "ghostuser", "due": "qachondir"},
    ],
})  # fmt: skip


async def make(engine: AsyncEngine, tmp_path: Path, ai: FakeAIClient | None) -> Harness:
    harness = build_harness(engine, tmp_path, chat_admins=(ADMIN.id,))
    settings = Settings(
        bot_token="123456:TEST",  # type: ignore[arg-type]
        allowed_chat_ids=[GROUP_ID],
        database_url=database_url(tmp_path),
    )
    harness.dp = create_dispatcher(settings, create_sessionmaker(engine), ai_client=ai)
    harness.dp["ai_guard"].cooldown_seconds = 0
    await introduce(harness)
    return harness


@pytest.fixture
async def h(engine: AsyncEngine, tmp_path: Path) -> AsyncIterator[Harness]:
    harness = await make(engine, tmp_path, FakeAIClient(PROPOSAL, "Ali #1 ustida ishlayapti <b>"))
    yield harness
    await harness.bot.session.close()


async def test_disabled_without_a_key(engine: AsyncEngine, tmp_path: Path) -> None:
    harness = await make(engine, tmp_path, None)
    await harness.say(ALI, "/ai standup")
    assert "ANTHROPIC_API_KEY" in harness.session.last_text()
    await harness.bot.session.close()


async def test_tasks_from_a_discussion(h: Harness) -> None:
    discussion = await h.say(VALI, "Ali, ertaga login xatosini tuzat. To'lov sahifasini ham.")
    await h.say(ALI, "/ai tasks", reply_to=discussion)
    assert "O'ylayapman" in h.session.last_text()
    proposal = h.session.edited()[-1]
    assert "Login xatosini tuzatish" in h.session.last_edit()
    assert "To'lov &lt;sahifasi&gt;" in h.session.last_edit()  # model output is escaped
    buttons = [b.callback_data for row in proposal.reply_markup.inline_keyboard for b in row]  # type: ignore[union-attr]
    create_all = next(b for b in buttons if b and b.endswith(":all"))

    await h.press(VALI, create_all, on=None)
    assert "so'rov yuborgan odam" in h.session.last_alert()  # only the requester confirms

    await h.press(ALI, create_all)
    assert "2 ta vazifa yaratildi" in h.session.last_edit()
    await h.say(ALI, "/info 1")
    card = h.session.last_text()
    assert "Login xatosini tuzatish" in card
    assert "Mas'ul: Ali" in card  # known username was assigned
    assert "Yuqori" in card
    assert "Muddat" in card  # "ertaga" became a date
    await h.say(ALI, "/info 2")
    assert "hali tayinlanmagan" in h.session.last_text()  # unknown username was ignored

    await h.press(ALI, create_all)
    assert "muddati o'tgan" in h.session.last_alert()  # a proposal is used only once


async def test_dismiss_and_question(h: Harness) -> None:
    await h.say(ALI, "/ai tasks Ali login xatosini tuzatsin, muhim")
    proposal = h.session.edited()[-1]
    buttons = [b.callback_data for row in proposal.reply_markup.inline_keyboard for b in row]  # type: ignore[union-attr]
    await h.press(ALI, next(b for b in buttons if b and b.endswith(":no")))
    assert "bekor qilindi" in h.session.last_edit()

    await h.say(ALI, "/ai Ali nima ustida ishlayapti?")
    answer = h.session.last_edit()
    assert "Javob" in answer
    assert "&lt;b&gt;" in answer  # never trusted as HTML


async def test_usage_and_errors(engine: AsyncEngine, tmp_path: Path) -> None:
    harness = await make(engine, tmp_path, FakeAIClient(AppError("ai_busy")))
    await harness.say(ALI, "/ai")
    assert "Foydalanish" in harness.session.last_text()
    await harness.say(ALI, "/ai tasks")
    assert "Foydalanish" in harness.session.last_text()
    await harness.say(ALI, "/ai standup")
    assert "band" in harness.session.last_edit()
    await harness.bot.session.close()
