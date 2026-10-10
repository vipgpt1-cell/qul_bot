from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any
from zoneinfo import ZoneInfo

from aiogram import BaseMiddleware, Bot
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from qul_bot.bot.context import RequestContext
from qul_bot.config import Settings
from qul_bot.domain.enums import Role
from qul_bot.i18n import Translator
from qul_bot.services.users import UserService
from qul_bot.services.workspaces import WorkspaceService

log = logging.getLogger(__name__)

Handler = Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]


class DbSessionMiddleware(BaseMiddleware):
    """One database transaction per Telegram update: commit on success, roll back on error.

    Handlers do their database work first and send messages last, so a failed send rolls the
    change back instead of leaving a task the user never saw confirmed.
    """

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self.sessionmaker = sessionmaker

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        async with self.sessionmaker() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
            except BaseException:
                await session.rollback()
                raise
            await session.commit()
            return result


class ContextMiddleware(BaseMiddleware):
    """Resolves the acting user and workspace and enforces the chat allow-list.

    Runs only for updates that matched a command or button, never for ordinary chatter.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        message = event.message if isinstance(event, CallbackQuery) else event
        tg_user = getattr(event, "from_user", None)
        if isinstance(event, CallbackQuery) and not isinstance(message, Message):
            # Telegram hides messages older than 48 hours; we cannot edit them any more.
            await event.answer(
                Translator(self.settings.default_locale)("err.stale_button"), show_alert=True
            )
            return None
        if not isinstance(message, Message) or tg_user is None or tg_user.is_bot:
            return None

        session: AsyncSession = data["session"]
        users, workspaces = UserService(session), WorkspaceService(session)
        user = await users.upsert_telegram(
            tg_user.id, tg_user.username, tg_user.first_name, tg_user.last_name
        )

        chat = message.chat
        if chat.type == ChatType.PRIVATE:
            found = await workspaces.sole_workspace_of(user.id)
            workspace, membership = found if found else (None, None)
        elif chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            workspace = await workspaces.find_by_chat(chat.id)
            if workspace is None:
                if chat.id not in self.settings.allowed_chat_ids:
                    log.warning(
                        "Ignoring chat %s (%r): not in ALLOWED_CHAT_IDS. "
                        "Run /chatid there to get the id to allow.",
                        chat.id,
                        chat.title,
                    )
                    return None
                workspace = await workspaces.create(
                    chat.id,
                    chat.title or "",
                    self.settings.default_locale,
                    self.settings.default_timezone,
                )
            if chat.title and workspace.title != chat.title:
                workspace.title = chat.title
            membership = await workspaces.get_membership(workspace.id, user.id)
            if membership is None:
                role = await self._initial_role(data["bot"], chat.id, tg_user.id)
                membership = await workspaces.add_member(workspace.id, user, role)
            if tg_user.id in self.settings.admin_user_ids and membership.role is not Role.ADMIN:
                membership = await workspaces.set_role(workspace.id, user, Role.ADMIN)
        else:
            return None

        data["ctx"] = RequestContext(
            user=user,
            workspace=workspace,
            membership=membership,
            tz=ZoneInfo(workspace.timezone if workspace else self.settings.default_timezone),
            t=Translator(workspace.locale if workspace else self.settings.default_locale),
        )
        # Remember who we saw even if their command fails: only the handler's own work should
        # roll back. (Otherwise a denied first command would leave the person unknown, and
        # nobody could then `/assign` or `/role` them by @username.)
        await session.commit()
        return await handler(event, data)

    @staticmethod
    async def _initial_role(bot: Bot, chat_id: int, telegram_id: int) -> Role:
        """Telegram group admins start as bot admins; everyone else as plain members."""
        try:
            member = await bot.get_chat_member(chat_id, telegram_id)
        except TelegramAPIError:
            log.exception("Could not read chat member status for %s in %s", telegram_id, chat_id)
            return Role.MEMBER
        if member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR):
            return Role.ADMIN
        return Role.MEMBER


def update_message(update: Update) -> Message | None:
    if update.message:
        return update.message
    if update.callback_query and isinstance(update.callback_query.message, Message):
        return update.callback_query.message
    return None
