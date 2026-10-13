"""End-to-end: real dispatcher, real handlers, real database, fake Telegram."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from aiogram import Bot
from aiogram.types import Chat
from sqlalchemy.ext.asyncio import AsyncEngine

from qul_bot.bot.app import create_dispatcher
from qul_bot.config import Settings
from qul_bot.db.session import create_sessionmaker
from tests.conftest import database_url
from tests.fake_telegram import GROUP_ID, FakeSession, Harness, tg_user

ADMIN = tg_user(1, "adminuser", "Admin")
REVIEWER = tg_user(2, "reviewer1", "Reviewer")
ALI = tg_user(3, "devalisher", "Ali")
VALI = tg_user(4, "devvalijon", "Vali")
STRANGER = tg_user(9, "strangerx", "Stranger")


def build_harness(
    engine: AsyncEngine,
    tmp_path: Path,
    *,
    chat_admins: tuple[int, ...] = (),
    admin_user_ids: tuple[int, ...] = (),
) -> Harness:
    session = FakeSession()
    session.chat_admins.update(chat_admins)
    bot = Bot("123456:TEST", session=session)
    settings = Settings(
        bot_token="123456:TEST",  # type: ignore[arg-type]
        allowed_chat_ids=[GROUP_ID],
        admin_user_ids=list(admin_user_ids),
        database_url=database_url(tmp_path),
    )
    return Harness(create_dispatcher(settings, create_sessionmaker(engine)), bot, session)


@pytest.fixture
async def bot_env(engine: AsyncEngine, tmp_path: Path) -> AsyncIterator[Harness]:
    harness = build_harness(engine, tmp_path, chat_admins=(ADMIN.id,))
    yield harness
    await harness.bot.session.close()


async def introduce(h: Harness) -> None:
    """Everybody says hello so the bot knows them (it only sees people who interact)."""
    for user in (ADMIN, REVIEWER, ALI, VALI):
        await h.say(user, "/team")
    await h.say(ADMIN, "/role @reviewer1 reviewer")
    h.session.reset()


# ---- access control -------------------------------------------------------------------


async def test_help_and_chatid_work_everywhere(bot_env: Harness) -> None:
    await bot_env.say(STRANGER, "/help", chat_id=-100777, chat_type="supergroup")
    assert "Qul Bot" in bot_env.session.last_text()
    await bot_env.say(STRANGER, "/chatid", chat_id=-100777, chat_type="supergroup")
    assert "-100777" in bot_env.session.last_text()


async def test_unlisted_group_is_ignored(bot_env: Harness) -> None:
    await bot_env.say(STRANGER, "/task Sneaky #x", chat_id=-100777, chat_type="supergroup")
    await bot_env.say(STRANGER, "/list", chat_id=-100777, chat_type="supergroup")
    assert bot_env.session.sent() == []


async def test_unknown_commands_are_ignored(bot_env: Harness) -> None:
    await bot_env.say(ALI, "/definitelynotacommand")
    assert bot_env.session.sent() == []


async def test_configured_admin_ids_work_when_telegram_reports_nobody(
    engine: AsyncEngine, tmp_path: Path
) -> None:
    """The recovery path: the bot is not a group admin, so it cannot see who the admins are."""
    h = build_harness(engine, tmp_path, admin_user_ids=(ALI.id,))
    try:
        await h.say(VALI, "/addarea mobile")
        assert "faqat adminlar" in h.session.last_text()
        await h.say(ALI, "/addarea mobile")  # ALI is listed in ADMIN_USER_IDS
        assert "Yo'nalish qo'shildi" in h.session.last_text()
        await h.say(ALI, "/role @devvalijon reviewer")
        assert "Tekshiruvchi" in h.session.last_text()
    finally:
        await h.bot.session.close()


async def test_chatid_shows_user_id_for_bootstrap(bot_env: Harness) -> None:
    await bot_env.say(ALI, "/chatid")
    text = bot_env.session.last_text()
    assert str(GROUP_ID) in text
    assert f"<code>{ALI.id}</code>" in text


async def test_telegram_admin_becomes_bot_admin_others_are_members(bot_env: Harness) -> None:
    await bot_env.say(ADMIN, "/team")
    await bot_env.say(ALI, "/team")
    text = bot_env.session.last_text()
    assert "👑 Admin" in text
    assert "👤 Ali" in text


# ---- creating tasks -------------------------------------------------------------------


async def test_create_task_with_all_tokens(bot_env: Harness) -> None:
    await introduce(bot_env)
    await bot_env.say(ADMIN, "/addarea mobile Mobil ilova")
    await bot_env.say(
        ALI, "/task Login xatosini tuzatish #mobile @devvalijon !yuqori muddat:ertaga"
    )
    card = bot_env.session.sent()[-1]
    assert "Vazifa yaratildi" in card.text
    assert "<b>#1</b>" in card.text
    assert "Login xatosini tuzatish" in card.text
    assert "Mobil ilova" in card.text
    assert "🟠 Yuqori" in card.text
    assert "tg://user?id=4" in card.text  # the assignee is pinged
    assert card.reply_markup is not None


async def test_create_from_reply_uses_the_replied_message(bot_env: Harness) -> None:
    await introduce(bot_env)
    original = await bot_env.say(VALI, "Ilova ochilganda crash bo'layapti")
    await bot_env.say(ALI, "/task", reply_to=original)
    card = bot_env.session.sent()[-1]
    assert "Ilova ochilganda crash bo'layapti" in card.text
    assert card.reply_parameters is not None
    assert card.reply_parameters.message_id == original.message_id
    assert "https://t.me/c/1234567890/" in card.text  # link back to the source message


async def test_create_without_title_explains_usage(bot_env: Harness) -> None:
    await introduce(bot_env)
    await bot_env.say(ALI, "/task")
    assert "Vazifa nomini yozing" in bot_env.session.last_text()


async def test_create_with_unknown_area_or_user_creates_nothing(bot_env: Harness) -> None:
    await introduce(bot_env)
    await bot_env.say(ALI, "/task Something #nope")
    assert "yo'nalishi topilmadi" in bot_env.session.last_text()
    await bot_env.say(ALI, "/task Something @ghostuser")
    assert "topilmadi" in bot_env.session.last_text()
    await bot_env.say(ALI, "/list")
    assert "Hozircha vazifa yo'q" in bot_env.session.last_text()


async def test_bad_deadline_is_explained(bot_env: Harness) -> None:
    await introduce(bot_env)
    await bot_env.say(ALI, "/task Something muddat:kelasi")
    assert "Muddatni tushunmadim" in bot_env.session.last_text()


# ---- the review workflow --------------------------------------------------------------


async def test_review_workflow_with_commands(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Fix crash @devalisher")

    await h.say(ALI, "/doing 1")
    assert "ustida ish boshlandi" in h.session.last_text()

    await h.say(ALI, "/done 1")  # developers finish into review...
    notice = h.session.last_text()
    assert "tekshiruvga yuborildi" in notice
    assert "tg://user?id=2" in notice  # ...and the reviewer is pinged

    await h.say(ALI, "/approve 1")  # developers cannot approve
    assert "faqat tekshiruvchi yoki admin" in h.session.last_text()

    await h.say(REVIEWER, "/reject 1 test yozing")
    rejected = h.session.last_text()
    assert "qaytarildi" in rejected
    assert "test yozing" in rejected
    assert "tg://user?id=3" in rejected  # the developer is pinged

    await h.say(ALI, "/done 1")
    await h.say(REVIEWER, "/done 1")  # a reviewer's /done approves
    assert "bajarildi va tasdiqlandi" in h.session.last_text()

    await h.say(ALI, "/list")
    assert "Hozircha vazifa yo'q" in h.session.last_text()
    await h.say(ALI, "/list all")
    assert "Fix crash" in h.session.last_text()


async def test_buttons_drive_the_same_workflow(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Fix crash @devalisher")
    card = h.session.sent()[-1]
    assert any(d.startswith("ta:start:") for d in h.session.buttons(card))

    await h.press(ALI, "ta:start:1")
    assert "Jarayonda" in h.session.last_edit()

    await h.press(ALI, "ta:ready:1")
    assert "Tekshiruvda" in h.session.last_edit()
    assert "tg://user?id=2" in h.session.last_text()  # reviewer notice as a new message

    h.session.reset()
    await h.press(ALI, "ta:approve:1")  # not allowed: alert, no edit
    assert h.session.edited() == []
    assert "faqat tekshiruvchi yoki admin" in h.session.last_alert()

    await h.press(REVIEWER, "ta:approve:1")
    assert "Bajarildi" in h.session.last_edit()


async def test_assign_me_and_priority_buttons(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Anyone can take this")
    await h.press(VALI, "ta:me:1")
    assert "Vali" in h.session.last_edit()
    await h.press(VALI, "ta:prio:1")
    assert "Yuqori" in h.session.last_edit()


async def test_stale_button_on_deleted_task_alerts(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Temporary")
    await h.say(ALI, "/delete 1")
    await h.press(ALI, "ta:delyes:1")
    assert "o'chirildi" in h.session.last_edit()
    h.session.reset()
    await h.press(ALI, "ta:start:1")
    assert "topilmadi" in h.session.last_alert()


async def test_delete_requires_author_or_admin(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Mine")
    await h.say(VALI, "/delete 1")
    assert "faqat muallifi yoki admin" in h.session.last_text()
    await h.say(ADMIN, "/delete 1")
    assert "o'chirilsinmi" in h.session.last_text()


# ---- editing --------------------------------------------------------------------------


async def test_edit_assign_comment_and_info(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ADMIN, "/addarea backend")
    await h.say(ALI, "/task Old title")
    await h.say(ALI, "/edit 1 New title #backend !shoshilinch muddat:3d")
    card = h.session.last_text()
    assert "New title" in card
    assert "🔴 Shoshilinch" in card
    assert "backend" in card

    await h.say(ALI, "/assign 1 @devvalijon")
    assert "tg://user?id=4" in h.session.last_text()
    await h.say(ALI, "/assign 1 @devvalijon")
    assert "allaqachon" in h.session.last_text()

    await h.say(VALI, "/comment 1 Men boshlayman")
    await h.say(VALI, "/info 1")
    assert "Men boshlayman" in h.session.last_text()

    await h.say(ALI, "/t1")  # the tappable shortcut used in lists
    assert "New title" in h.session.last_text()

    await h.say(ALI, "/unassign 1 @devvalijon")
    assert "mas'uliyatdan olindi" in h.session.last_text()


async def test_assign_by_replying_to_someone(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Whoever")
    their_message = await h.say(VALI, "I can do it")
    await h.say(ALI, "/assign 1", reply_to=their_message)
    assert "tg://user?id=4" in h.session.last_text()


async def test_strangers_cannot_modify_assigned_tasks(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Private work @devalisher")
    await h.say(VALI, "/edit 1 Hijacked")
    assert "mas'ul, muallif" in h.session.last_text()
    await h.say(VALI, "/doing 1")
    assert "mas'ul, muallif" in h.session.last_text()


async def test_task_ref_errors(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/done")
    assert "Vazifa raqamini yozing" in h.session.last_text()
    await h.say(ALI, "/done 404")
    assert "404" in h.session.last_text()
    assert "topilmadi" in h.session.last_text()


# ---- lists ----------------------------------------------------------------------------


async def test_lists_my_review_digest_and_area_shortcut(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ADMIN, "/addarea mobile Mobil")
    await h.say(ALI, "/task Alpha #mobile @devalisher !high muddat:bugun")
    await h.say(ALI, "/task Beta @devvalijon")
    await h.say(ALI, "/task Gamma")
    await h.say(ALI, "/ready 1")

    await h.say(ALI, "/my")
    mine = h.session.last_text()
    assert "Alpha" in mine
    assert "Beta" not in mine

    await h.say(REVIEWER, "/review")
    assert "Alpha" in h.session.last_text()

    await h.say(ALI, "/mobile")  # area shortcut
    assert "#mobile" in h.session.last_text()
    assert "Alpha" in h.session.last_text()
    assert "Beta" not in h.session.last_text()

    await h.say(ALI, "/list @devvalijon")
    assert "Beta" in h.session.last_text()
    assert "Alpha" not in h.session.last_text()

    await h.say(ALI, "/digest")
    digest = h.session.last_text()
    assert "Xulosa" in digest
    assert "Bugun muddati" in digest
    assert "Tekshiruv kutmoqda" in digest
    assert "Mas'ulsiz" in digest


async def test_list_pagination_buttons(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    for i in range(17):
        await h.say(ALI, f"/task Task number {i}")
    await h.say(ALI, "/list")
    page_one = h.session.sent()[-1]
    assert "Jami: 17" in page_one.text
    next_page = h.session.buttons(page_one)[-1]

    await h.press(ALI, next_page)
    page_two = h.session.last_edit()
    assert "Task number 16" in page_two
    assert "Task number 0" not in page_two


async def test_unknown_area_in_list_is_reported(bot_env: Harness) -> None:
    await introduce(bot_env)
    await bot_env.say(ALI, "/list nonexistent")
    assert "yo'nalishi topilmadi" in bot_env.session.last_text()


async def test_html_in_user_text_is_escaped(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Fix <b>bold</b> & <script>")
    card = h.session.last_text()
    assert "&lt;b&gt;bold&lt;/b&gt; &amp; &lt;script&gt;" in card


# ---- admin ----------------------------------------------------------------------------


async def test_admin_commands_are_admin_only(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/addarea mobile")
    assert "faqat adminlar" in h.session.last_text()
    await h.say(ALI, "/role @devvalijon admin")
    assert "faqat adminlar" in h.session.last_text()


async def test_area_management(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ADMIN, "/addarea mobile Mobil ilova")
    assert "Yo'nalish qo'shildi" in h.session.last_text()
    await h.say(ADMIN, "/addarea mobile")
    assert "allaqachon mavjud" in h.session.last_text()
    await h.say(ADMIN, "/addarea task")
    assert "buyruq sifatida band" in h.session.last_text()
    await h.say(ADMIN, "/addarea")
    assert "Foydalanish" in h.session.last_text()
    await h.say(ALI, "/areas")
    assert "Mobil ilova" in h.session.last_text()
    await h.say(ADMIN, "/delarea mobile")
    assert "o'chirildi" in h.session.last_text()


async def test_role_changes(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ADMIN, "/role @devvalijon reviewer")
    assert "Tekshiruvchi" in h.session.last_text()
    their_message = await h.say(ALI, "hello")
    await h.say(ADMIN, "/role member", reply_to=their_message)
    assert "Ali" in h.session.last_text()
    await h.say(ADMIN, "/role @adminuser member")
    assert "Oxirgi adminni" in h.session.last_text()


# ---- private chat & migration ---------------------------------------------------------


async def test_private_chat_resolves_the_only_workspace(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Work item @devalisher")
    await h.say(ALI, "/my", chat_id=ALI.id, chat_type="private")
    assert "Work item" in h.session.last_text()
    await h.say(ALI, "/doing 1", chat_id=ALI.id, chat_type="private")
    assert "ustida ish boshlandi" in h.session.last_text()


async def test_private_chat_without_a_workspace_explains(bot_env: Harness) -> None:
    await bot_env.say(STRANGER, "/my", chat_id=STRANGER.id, chat_type="private")
    assert "guruh" in bot_env.session.last_text()


async def test_group_upgrade_to_supergroup_keeps_working(bot_env: Harness) -> None:
    from datetime import UTC, datetime

    from aiogram.types import Chat, Message, Update

    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Survives the upgrade")
    new_id = -1009876543210
    service_message = Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=GROUP_ID, type="group"),
        migrate_to_chat_id=new_id,
    )
    await h.dp.feed_update(h.bot, Update(update_id=999, message=service_message))

    await h.say(ALI, "/list", chat_id=new_id)
    assert "Survives the upgrade" in h.session.last_text()


# ---- the rest of the workflow commands ------------------------------------------------


async def test_block_cancel_reopen_and_restore(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Waiting on API @devalisher")

    await h.say(ALI, "/block 1 backend kutilmoqda")
    notice = h.session.last_text()
    assert "bloklandi" in notice
    assert "backend kutilmoqda" in notice
    await h.say(ALI, "/info 1")
    assert "backend kutilmoqda" in h.session.last_text()  # the reason is kept as a comment

    await h.say(ALI, "/doing 1")  # unblock
    assert "ustida ish boshlandi" in h.session.last_text()

    await h.say(ALI, "/cancel 1 kerak emas")
    assert "bekor qilindi" in h.session.last_text()
    await h.say(ALI, "/reopen 1")
    assert "qayta ochildi" in h.session.last_text()

    await h.say(ADMIN, "/delete 1")
    await h.press(ADMIN, "ta:delyes:1")
    await h.say(ALI, "/info 1")
    assert "topilmadi" in h.session.last_text()
    await h.say(ALI, "/restore 1")
    assert "faqat adminlar" in h.session.last_text()
    await h.say(ADMIN, "/restore 1")
    assert "qayta tiklandi" in h.session.last_text()
    await h.say(ALI, "/info 1")
    assert "Waiting on API" in h.session.last_text()


async def test_only_reviewers_reopen_done_tasks(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Ship it @devalisher")
    await h.say(ALI, "/done 1")
    await h.say(REVIEWER, "/approve 1")
    await h.say(ALI, "/reopen 1")
    assert "faqat tekshiruvchi yoki admin" in h.session.last_text()
    await h.say(REVIEWER, "/reopen 1")
    assert "qayta ochildi" in h.session.last_text()


async def test_reviewer_cannot_approve_their_own_assignment(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(REVIEWER, "/task My own work @reviewer1")
    await h.say(REVIEWER, "/done 1")
    assert "tekshiruvga yuborildi" in h.session.last_text()
    await h.say(REVIEWER, "/done 1")
    assert "o'zingiz tasdiqlay olmaysiz" in h.session.last_text()
    await h.say(ADMIN, "/approve 1")  # an admin can
    assert "bajarildi va tasdiqlandi" in h.session.last_text()


async def test_invalid_transitions_are_explained_with_readable_statuses(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Fresh")
    await h.say(ALI, "/approve 1")
    text = h.session.last_text()
    assert "Kutilmoqda" in text  # statuses are translated, never raw codes like "todo"
    assert "Bajarildi" in text
    await h.say(ALI, "/doing 1")
    await h.say(ALI, "/doing 1")
    assert "allaqachon shu holatda" in h.session.last_text()
    assert "Jarayonda" in h.session.last_text()


async def test_button_on_an_expired_message_tells_the_user(bot_env: Harness) -> None:
    from aiogram.types import CallbackQuery, InaccessibleMessage, Update

    h = bot_env
    await introduce(h)
    old = InaccessibleMessage(chat=Chat(id=GROUP_ID, type="supergroup"), message_id=1)
    query = CallbackQuery(id="1", from_user=ALI, chat_instance="x", message=old, data="ta:start:1")
    await h.dp.feed_update(h.bot, Update(update_id=777, callback_query=query))
    assert "eskirgan" in h.session.last_alert()


async def test_a_denied_first_command_still_registers_the_person(bot_env: Harness) -> None:
    """Failures roll back the command's work, not the fact that we met the person."""
    h = bot_env
    await h.say(ADMIN, "/team")
    await h.say(VALI, "/addarea mobile")  # VALI's very first command, and it is denied
    assert "faqat adminlar" in h.session.last_text()
    await h.say(ADMIN, "/role @devvalijon reviewer")
    assert "Tekshiruvchi" in h.session.last_text()


# ---- specialties and the assignee picker ----------------------------------------------


async def test_specialty_by_text_and_by_admin(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/specialty backend")
    assert "Backend" in h.session.last_text()
    await h.say(VALI, "/specialty @devalisher qa")  # members cannot set other people's
    assert "faqat adminlar" in h.session.last_text()
    await h.say(ADMIN, "/specialty @devvalijon mobile")
    assert "Mobile" in h.session.last_text()
    their_message = await h.say(ALI, "hello")
    await h.say(ADMIN, "/specialty devops", reply_to=their_message)
    assert "DevOps" in h.session.last_text()
    await h.say(ALI, "/specialty -")
    assert "Belgilanmagan" in h.session.last_text()


async def test_specialty_errors(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/specialty designer")
    assert "Mutaxassislik topilmadi" in h.session.last_text()
    assert "devops" in h.session.last_text()
    await h.say(ALI, "/specialty @devvalijon")
    assert "Foydalanish" in h.session.last_text()


async def test_specialty_buttons_set_your_own(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/specialty")
    buttons = h.session.buttons(h.session.sent()[-1])
    assert len(buttons) == 8  # seven specialties + clear
    backend = next(b for b in buttons if b == "sp:3")
    await h.press(ALI, backend)
    assert "Backend" in h.session.last_edit()
    await h.say(ALI, "/team")
    assert "Backend" in h.session.last_text()


async def test_team_is_grouped_by_specialty(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/specialty backend")
    await h.say(VALI, "/specialty mobile")
    await h.say(ADMIN, "/team")
    text = h.session.last_text()
    assert text.index("Mobile") < text.index("Backend") < text.index("Belgilanmagan")
    assert "Ali" in text
    assert "Vali" in text


async def test_picker_assigns_people_by_specialty(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/specialty backend")
    await h.say(VALI, "/specialty mobile")
    await h.say(ADMIN, "/task Build the API")
    card = h.session.sent()[-1]
    assert any(b.startswith("ta:assign:") for b in h.session.buttons(card))

    await h.press(ADMIN, "ta:assign:1")  # step 1: groups with counts
    menu = h.session.last_edit()
    assert "Kimga tayinlaymiz" in menu
    edited = h.session.edited()[-1]
    labels = [
        b.text
        for row in edited.reply_markup.inline_keyboard  # type: ignore[union-attr]
        for b in row
    ]
    assert any("Mobile (1)" in label for label in labels)
    assert any("Backend (1)" in label for label in labels)
    assert any("Belgilanmagan (2)" in label for label in labels)  # admin + reviewer

    backend = next(
        b.callback_data
        for row in edited.reply_markup.inline_keyboard  # type: ignore[union-attr]
        for b in row
        if "Backend" in b.text and b.callback_data
    )
    await h.press(ADMIN, backend)  # step 2: people in that group
    assert "Backend" in h.session.last_edit()

    group_markup = h.session.edited()[-1].reply_markup
    ali_button = next(
        b.callback_data
        for row in group_markup.inline_keyboard  # type: ignore[union-attr]
        for b in row
        if "Ali" in b.text and b.callback_data
    )
    h.session.reset()
    await h.press(ADMIN, ali_button)  # pick Ali
    assert "tg://user?id=3" in h.session.last_text()  # Ali is pinged
    assert "Mas'ul: Ali" in h.session.last_edit()

    await h.say(ADMIN, "/info 1")
    assert "Mas'ul: Ali" in h.session.last_text()

    await h.press(ADMIN, ali_button)  # pressing again removes
    assert "hali tayinlanmagan" in h.session.last_edit()


async def test_picker_close_restores_the_card_buttons(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ADMIN, "/task Something")
    await h.press(ADMIN, "ta:assign:1")
    await h.press(ADMIN, "ap:1:close:0:0")
    markup = h.session.edited()[-1].reply_markup
    data = [b.callback_data for row in markup.inline_keyboard for b in row]  # type: ignore[union-attr]
    assert any(d and d.startswith("ta:start:") for d in data)


async def test_picker_respects_task_permissions(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Private work @devalisher")
    await h.press(VALI, "ta:assign:1")  # opening is harmless
    h.session.reset()
    await h.press(VALI, "ap:1:user:0:4")  # but changing an assigned task is not allowed
    assert "mas'ul, muallif" in h.session.last_alert()


async def test_old_commands_unaffected_by_new_button(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Fix crash")
    data = h.session.buttons(h.session.sent()[-1])
    assert {"ta:start:1", "ta:ready:1", "ta:me:1", "ta:assign:1", "ta:prio:1"} <= set(data)
    assert all(len(d.encode()) <= 64 for d in data)


# ---- comfort features -----------------------------------------------------------------


async def test_replying_to_a_card_needs_no_task_number(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Fix crash @devalisher")
    card = h.last_bot_message()

    await h.say(ALI, "/doing", reply_to=card)
    assert "ustida ish boshlandi" in h.session.last_text()
    await h.say(ALI, "/comment Boshladim", reply_to=card)
    assert "Boshladim" in h.session.last_text()
    await h.say(ALI, "/info", reply_to=card)
    assert "Boshladim" in h.session.last_text()
    await h.say(ADMIN, "/assign @devvalijon", reply_to=card)
    assert "tg://user?id=4" in h.session.last_text()
    await h.say(ALI, "/done", reply_to=card)
    assert "tekshiruvga yuborildi" in h.session.last_text()
    await h.say(REVIEWER, "/approve", reply_to=h.last_bot_message())  # a status notice works too
    assert "bajarildi va tasdiqlandi" in h.session.last_text()


async def test_an_explicit_number_beats_the_replied_card(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task First")
    first_card = h.last_bot_message()
    await h.say(ALI, "/task Second")
    await h.say(ALI, "/info 2", reply_to=first_card)
    assert "Second" in h.session.last_text()


async def test_replying_to_a_card_with_task_does_not_clone_the_card(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Real task")
    await h.say(ALI, "/task", reply_to=h.last_bot_message())
    assert "Vazifa nomini yozing" in h.session.last_text()
    await h.say(ALI, "/list")
    assert "Jami: 1" in h.session.last_text()


async def test_replying_to_a_non_card_still_asks_for_a_number(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Something")
    await h.say(ALI, "/list")
    await h.say(ALI, "/done", reply_to=h.last_bot_message())
    assert "Vazifa raqamini yozing" in h.session.last_text()


async def test_history_command(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Tracked work @devalisher")
    await h.say(ALI, "/doing 1")
    await h.say(ALI, "/done 1")
    await h.say(REVIEWER, "/reject 1 testlar yo'q")
    await h.say(ALI, "/history 1")
    text = h.session.last_text()
    assert "tarixi" in text
    assert "yaratdi" in text
    assert "⚪ Kutilmoqda → 🔵 Jarayonda" in text
    assert "🔵 Jarayonda → 👀 Tekshiruvda" in text
    assert "👀 Tekshiruvda → 🔵 Jarayonda" in text  # the rejection
    assert "testlar yo'q" in text
    # the history message itself names the task, so replying to it works as well
    await h.say(ALI, "/info", reply_to=h.last_bot_message())
    assert "Tracked work" in h.session.last_text()


async def test_find_command(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/task Login crash on iOS")
    await h.say(ALI, "/task Update the docs\nmentions the login flow")
    await h.say(ALI, "/task Unrelated")
    await h.say(ALI, "/find LOGIN")
    text = h.session.last_text()
    assert "Qidiruv" in text
    assert "Login crash" in text
    assert "Update the docs" in text  # found through its description
    assert "Unrelated" not in text
    await h.say(ALI, "/find zzzz")
    assert "hech narsa topilmadi" in h.session.last_text()
    await h.say(ALI, "/find x")
    assert "kamida 2 ta belgi" in h.session.last_text()
    await h.say(ALI, "/find")
    assert "kamida 2 ta belgi" in h.session.last_text()


async def test_digest_schedule_settings(bot_env: Harness) -> None:
    h = bot_env
    await introduce(h)
    await h.say(ALI, "/digest")
    assert "09:00" in h.session.last_text()  # the on-demand digest says when it posts by itself
    await h.say(ALI, "/digest 08:30")
    assert "faqat adminlar" in h.session.last_text()

    await h.say(ADMIN, "/digest 08:30")
    assert "08:30" in h.session.last_text()
    await h.say(ALI, "/digest")
    assert "08:30" in h.session.last_text()

    await h.say(ADMIN, "/digest off")
    assert "o'chirildi" in h.session.last_text()
    await h.say(ALI, "/digest")
    assert "o'chirilgan" in h.session.last_text()
    await h.say(ADMIN, "/digest on")
    assert "yoqildi" in h.session.last_text()

    await h.say(ADMIN, "/digest 25:99")
    assert "Vaqtni tushunmadim" in h.session.last_text()


async def test_help_is_a_menu_with_sections(bot_env: Harness) -> None:
    h = bot_env
    await h.say(ALI, "/help")
    main = h.session.sent()[-1]
    assert "Qul Bot" in main.text
    buttons = h.session.buttons(main)
    assert sorted(buttons) == ["hp:create", "hp:team", "hp:view", "hp:workflow"]

    await h.press(ALI, "hp:workflow")
    assert "Tekshiruvda" in h.session.last_edit()
    assert "/done" in h.session.last_edit()
    assert h.session.edited()[-1].reply_markup is not None

    await h.press(ALI, "hp:main")
    assert "Bo'limni tanlang" in h.session.last_edit()
    await h.press(ALI, "hp:nonsense")  # unknown page: ignored, no crash
