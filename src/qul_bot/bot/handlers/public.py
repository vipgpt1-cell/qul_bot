"""Handlers that work anywhere, before any workspace is resolved."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.i18n import DEFAULT_LOCALE, Translator
from qul_bot.services.workspaces import WorkspaceService


async def cmd_help(message: Message) -> None:
    await message.answer(Translator(DEFAULT_LOCALE)("help.text"))


async def cmd_chatid(message: Message) -> None:
    """Works in every chat: shows the ids needed for ALLOWED_CHAT_IDS and ADMIN_USER_IDS."""
    user_id = message.from_user.id if message.from_user else 0
    await message.answer(
        Translator(DEFAULT_LOCALE)("chatid.text", chat_id=message.chat.id, user_id=user_id)
    )


async def on_migrate_to(message: Message, session: AsyncSession) -> None:
    """The group became a supergroup and got a new id: keep its workspace."""
    assert message.migrate_to_chat_id is not None
    await WorkspaceService(session).migrate_chat(message.chat.id, message.migrate_to_chat_id)


async def on_migrate_from(message: Message, session: AsyncSession) -> None:
    assert message.migrate_from_chat_id is not None
    await WorkspaceService(session).migrate_chat(message.migrate_from_chat_id, message.chat.id)


async def on_noop(callback: CallbackQuery) -> None:
    await callback.answer()


def register(router: Router) -> None:
    router.message.register(cmd_help, Command("start", "help", ignore_case=True))
    router.message.register(cmd_chatid, Command("chatid", ignore_case=True))
    router.message.register(on_migrate_to, F.migrate_to_chat_id)
    router.message.register(on_migrate_from, F.migrate_from_chat_id)
    router.callback_query.register(on_noop, F.data == "noop")
