"""A fake Telegram API for driving the real dispatcher end to end.

`FakeTelegram` records every API call the bot makes and answers just enough of them
(`getMe`, `sendMessage`, `getChatMember`, ...) for handlers to run.
"""

from __future__ import annotations

import html
import re
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageText,
    GetChatMember,
    GetMe,
    SendMessage,
    TelegramMethod,
)
from aiogram.types import (
    CallbackQuery,
    Chat,
    ChatMemberMember,
    ChatMemberOwner,
    InlineKeyboardMarkup,
    Message,
    Update,
    User,
)

BOT_ID = 999
GROUP_ID = -1001234567890


def tg_user(user_id: int, username: str | None, name: str) -> User:
    return User(id=user_id, is_bot=False, first_name=name, username=username)


class FakeSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        self.chat_admins: set[int] = set()
        #: Survives reset(): buttons are pressed on the bot's latest message.
        self.last_message: SendMessage | None = None
        self._next_message_id = 5000

    async def close(self) -> None:
        return None

    async def stream_content(self, *args: Any, **kwargs: Any) -> AsyncGenerator[bytes, None]:
        yield b""

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        timeout: int | None = None,  # noqa: ASYNC109 (mirrors the aiogram signature)
    ) -> Any:
        self.calls.append(method)
        if isinstance(method, GetMe):
            return User(id=BOT_ID, is_bot=True, first_name="Qul", username="qul_test_bot")
        if isinstance(method, SendMessage):
            self.last_message = method
            self._next_message_id += 1
            return Message(
                message_id=self._next_message_id,
                date=datetime.now(UTC),
                chat=Chat(id=int(method.chat_id), type="supergroup"),
                from_user=User(id=BOT_ID, is_bot=True, first_name="Qul"),
                text=method.text,
            )
        if isinstance(method, EditMessageText):
            return Message(
                message_id=int(method.message_id or 0),
                date=datetime.now(UTC),
                chat=Chat(id=int(method.chat_id or 0), type="supergroup"),
                text=method.text,
            )
        if isinstance(method, GetChatMember):
            user = tg_user(method.user_id, None, "x")
            if method.user_id in self.chat_admins:
                return ChatMemberOwner(user=user, is_anonymous=False)
            return ChatMemberMember(user=user)
        if isinstance(method, AnswerCallbackQuery):
            return True
        return True

    # ---- helpers for assertions ---------------------------------------------------------

    def sent(self) -> list[SendMessage]:
        return [c for c in self.calls if isinstance(c, SendMessage)]

    def edited(self) -> list[EditMessageText]:
        return [c for c in self.calls if isinstance(c, EditMessageText)]

    def alerts(self) -> list[AnswerCallbackQuery]:
        return [c for c in self.calls if isinstance(c, AnswerCallbackQuery) and c.text]

    def last_text(self) -> str:
        return self.sent()[-1].text

    def last_edit(self) -> str:
        return self.edited()[-1].text or ""

    def last_alert(self) -> str:
        return self.alerts()[-1].text or ""

    @staticmethod
    def buttons(message: SendMessage) -> list[str]:
        """Callback data of every inline button on a sent message, in order."""
        markup = message.reply_markup
        assert isinstance(markup, InlineKeyboardMarkup), "message has no inline keyboard"
        return [b.callback_data or "" for row in markup.inline_keyboard for b in row]

    def reset(self) -> None:
        self.calls.clear()


class Harness:
    """Feeds updates to a real dispatcher and exposes what the bot answered."""

    def __init__(self, dp: Dispatcher, bot: Bot, session: FakeSession) -> None:
        self.dp, self.bot, self.session = dp, bot, session
        self._update_id = 0
        self._message_id = 0

    def _next_update(self) -> int:
        self._update_id += 1
        return self._update_id

    def message(
        self,
        user: User,
        text: str,
        *,
        chat_id: int = GROUP_ID,
        chat_type: str = "supergroup",
        reply_to: Message | None = None,
    ) -> Message:
        self._message_id += 1
        return Message(
            message_id=self._message_id,
            date=datetime.now(UTC),
            chat=Chat(id=chat_id, type=chat_type, title="IT Team" if chat_id < 0 else None),
            from_user=user,
            text=text,
            reply_to_message=reply_to,
        )

    def last_bot_message(self) -> Message:
        """The bot's latest message as Telegram would deliver it (plain text, no HTML tags)."""
        last = self.session.last_message
        assert last is not None, "the bot has not sent anything yet"
        plain = html.unescape(re.sub(r"<[^>]+>", "", last.text))
        return Message(
            message_id=9000,
            date=datetime.now(UTC),
            chat=Chat(id=int(last.chat_id), type="supergroup"),
            from_user=User(id=BOT_ID, is_bot=True, first_name="Qul"),
            text=plain,
        )

    async def say(self, user: User, text: str, **kwargs: Any) -> Message:
        """Send a message from `user`; returns it so tests can reply to it."""
        message = self.message(user, text, **kwargs)
        await self.dp.feed_update(self.bot, Update(update_id=self._next_update(), message=message))
        return message

    async def press(self, user: User, data: str, *, on: Message | None = None) -> None:
        """Press an inline button. By default on the bot's most recent message."""
        if on is None:
            last = self.session.last_message
            assert last is not None, "the bot has not sent anything to press a button on"
            on = Message(
                message_id=5000,
                date=datetime.now(UTC),
                chat=Chat(id=int(last.chat_id), type="supergroup"),
                from_user=User(id=BOT_ID, is_bot=True, first_name="Qul"),
                text=last.text,
            )
        query = CallbackQuery(
            id=str(self._next_update()),
            from_user=user,
            chat_instance="test",
            message=on,
            data=data,
        )
        await self.dp.feed_update(
            self.bot, Update(update_id=self._next_update(), callback_query=query)
        )
