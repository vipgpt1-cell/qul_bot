"""End-to-end QA features: testing step, checklists, bug reports, releases, files."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from aiogram.methods import SendPhoto
from aiogram.types import ForceReply
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.fake_telegram import Harness
from tests.test_bot_flow import ADMIN, ALI, REVIEWER, VALI, build_harness, introduce


@pytest.fixture
async def h(engine: AsyncEngine, tmp_path: Path) -> AsyncIterator[Harness]:
    harness = build_harness(engine, tmp_path, chat_admins=(ADMIN.id,))
    await introduce(harness)
    yield harness
    await harness.bot.session.close()


async def make_vali_tester(h: Harness) -> None:
    await h.say(ADMIN, "/specialty @devvalijon qa")
    h.session.reset()


# ---- testing step ---------------------------------------------------------------------


async def test_testing_step_with_commands(h: Harness) -> None:
    await make_vali_tester(h)
    await h.say(ALI, "/task Payment screen @devalisher")
    await h.say(ALI, "/done 1")
    await h.say(REVIEWER, "/approve 1")
    notice = h.session.last_text()
    assert "testga o'tdi" in notice
    assert "tg://user?id=4" in notice  # the tester is pinged

    await h.say(ALI, "/approve 1")
    assert "faqat QA yoki admin" in h.session.last_text()
    await h.say(VALI, "/reject 1 tugma ishlamayapti")
    failed = h.session.last_text()
    assert "testdan o'tmadi" in failed
    assert "tugma ishlamayapti" in failed
    assert "tg://user?id=3" in failed  # the developer is pinged

    await h.say(ALI, "/done 1")
    await h.say(REVIEWER, "/done 1")  # reviewer's /done -> testing
    await h.say(VALI, "/done 1")  # tester's /done -> done
    assert "bajarildi va tasdiqlandi" in h.session.last_text()


async def test_testing_step_with_buttons(h: Harness) -> None:
    await make_vali_tester(h)
    await h.say(ALI, "/task Button flow @devalisher")
    await h.press(ALI, "ta:ready:1")
    await h.press(REVIEWER, "ta:approve:1")
    assert "Testda" in h.session.last_edit()
    assert "tg://user?id=4" in h.session.last_text()  # the tester is pinged in the chat
    await h.press(VALI, "ta:approve:1")
    assert "Bajarildi" in h.session.last_edit()


async def test_without_testers_approve_means_done(h: Harness) -> None:
    await h.say(ALI, "/task No QA team @devalisher")
    await h.say(ALI, "/done 1")
    await h.say(REVIEWER, "/approve 1")
    assert "bajarildi va tasdiqlandi" in h.session.last_text()


async def test_qa_setting(h: Harness) -> None:
    await h.say(ALI, "/qa")
    assert "QA yo'q" in h.session.last_text()
    await make_vali_tester(h)
    await h.say(ALI, "/qa")
    assert "Vali" in h.session.last_text()
    await h.say(ALI, "/qa off")
    assert "faqat adminlar" in h.session.last_text()
    await h.say(ADMIN, "/qa off")
    assert "o'chirilgan" in h.session.last_text()
    await h.say(ALI, "/task Fast lane @devalisher")
    await h.say(ALI, "/done 1")
    await h.say(REVIEWER, "/approve 1")
    assert "bajarildi va tasdiqlandi" in h.session.last_text()
    await h.say(ADMIN, "/qa maybe")
    assert "Foydalanish" in h.session.last_text()


# ---- checklists -----------------------------------------------------------------------


async def test_checklist_commands_buttons_and_done_gate(h: Harness) -> None:
    await h.say(ALI, "/task Release build @devalisher")
    card = h.last_bot_message()
    await h.say(ALI, "/check Login ishlaydi; Dark mode\nPush xabarlar", reply_to=card)
    checklist = h.session.sent()[-1]
    assert "(0/3)" in checklist.text
    toggles = h.session.buttons(checklist)
    assert len(toggles) == 3

    await h.say(ALI, "/done 1")
    await h.say(REVIEWER, "/approve 1")
    assert "3 ta belgilanmagan" in h.session.last_text()

    for toggle in toggles:
        await h.press(REVIEWER, toggle, on=None)
    assert "(3/3)" in h.session.last_edit()
    await h.say(REVIEWER, "/approve 1")
    assert "bajarildi va tasdiqlandi" in h.session.last_text()


async def test_checklist_remove_and_card_progress(h: Harness) -> None:
    await h.say(ALI, "/task Has checks")
    await h.say(ALI, "/check 1 one; two")
    await h.say(ALI, "/check 1 -1")
    assert "(0/1)" in h.session.last_text()
    assert "two" in h.session.last_text()
    await h.say(ALI, "/info 1")
    assert "Tekshiruv ro'yxati: 0/1" in h.session.last_text()
    await h.say(ALI, "/check 1 -5")
    assert "topilmadi" in h.session.last_text()


async def test_checklist_button_on_the_card(h: Harness) -> None:
    await h.say(ALI, "/task Card button")
    assert "ta:checks:1" in h.session.buttons(h.session.sent()[-1])
    await h.press(ALI, "ta:checks:1")
    assert "Ro'yxat bo'sh" in h.session.last_text()


# ---- bug reports ----------------------------------------------------------------------


async def test_guided_bug_report(h: Harness) -> None:
    await h.say(ALI, "/bug #mobile")
    assert "yo'nalishi topilmadi" in h.session.last_text()  # validated before any question
    await h.say(ADMIN, "/addarea mobile")

    await h.say(ALI, "/bug #mobile v:1.4.0")
    first = h.session.sent()[-1]
    assert "1/6" in first.text
    assert isinstance(first.reply_markup, ForceReply)

    await h.say(ALI, "Login crashes")
    assert "2/6" in h.session.last_text()
    await h.say(ALI, "1. Open app\n2. Tap login")
    await h.say(ALI, "Home screen")
    await h.say(ALI, "App closes")
    await h.say(ALI, "-")  # skip the device question
    severity = h.session.sent()[-1]
    assert "Jiddiylik" in severity.text

    await h.press(VALI, "bs:critical", on=None)  # not Vali's form
    assert "boshqa odamning" in h.session.last_alert()
    await h.press(ALI, "bs:critical")
    assert "6/6" in h.session.last_text()

    await h.say(ALI, "", photo="SCREENSHOT-1")
    card = h.session.last_text()
    assert "Bug qayd etildi" in card
    assert "🐞 Bug" in card
    assert "Login crashes" in card
    assert "Tap login" in card
    assert "App closes" in card
    assert "Qurilma" not in card  # skipped answers stay out
    assert "🔴 Shoshilinch" in card
    assert "1.4.0" in card
    assert "Ilovalar: 1" in card

    await h.say(ALI, "/files 1")
    photos = h.session.calls_of(SendPhoto)
    assert [p.photo for p in photos] == ["SCREENSHOT-1"]

    await h.say(ALI, "/bugs")
    assert "Login crashes" in h.session.last_text()


async def test_quick_bug_and_cancel(h: Harness) -> None:
    await h.say(ALI, "/bug Checkout fails !high\nSteps: open cart, pay")
    card = h.session.last_text()
    assert "Bug qayd etildi" in card
    assert "open cart" in card

    await h.say(ALI, "/bug")
    await h.say(ALI, "/cancel")
    assert "bekor qilindi" in h.session.last_text()
    await h.say(ALI, "this is just chat now")
    assert "bekor qilindi" in h.session.last_text()  # no form is listening any more

    await h.say(ALI, "/task Not a bug")
    await h.say(ALI, "/bugs")
    assert "Checkout fails" in h.session.last_text()
    assert "Not a bug" not in h.session.last_text()


async def test_commands_still_work_during_the_form(h: Harness) -> None:
    await h.say(ALI, "/bug")
    await h.say(ALI, "/list")
    assert "Vazifalar" in h.session.last_text()
    await h.say(ALI, "Still my title")
    assert "2/6" in h.session.last_text()


# ---- releases -------------------------------------------------------------------------


async def test_release_report(h: Harness) -> None:
    await h.say(ALI, "/release")
    assert "Hali reliz yo'q" in h.session.last_text()
    await h.say(ALI, "/task Feature v:1.4.0 @devalisher")
    await h.say(ALI, "/bug Crash on start v:1.4.0 !urgent\nevery time")
    await h.say(ALI, "/task Later v:1.5.0")

    await h.say(ALI, "/release")
    listing = h.session.last_text()
    assert listing.index("1.5.0") < listing.index("1.4.0")

    await h.say(ALI, "/release v1.4.0")
    report = h.session.last_text()
    assert "Reliz 1.4.0" in report
    assert "tayyor emas" in report
    assert "Ochiq buglar: 1" in report
    assert "Crash on start" in report

    await h.say(ALI, "/done 1")
    await h.say(REVIEWER, "/approve 1")
    await h.say(ADMIN, "/cancel 2 duplicate")
    await h.say(ALI, "/release 1.4.0")
    assert "chiqarishga tayyor" in h.session.last_text()

    await h.say(ALI, "/release 9.9")
    assert "vazifa yo'q" in h.session.last_text()
    await h.say(ALI, "/edit 3 v:#bad")
    assert "Reliz nomini tushunmadim" in h.session.last_text()
