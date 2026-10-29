"""The command registry: names handled by the bot and the menus shown in Telegram."""

from __future__ import annotations

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)

from qul_bot.domain.enums import TaskStatus
from qul_bot.i18n import Translator

#: `/doing 42` style commands and the status each one moves a task to.
STATUS_COMMANDS: dict[str, TaskStatus] = {
    "doing": TaskStatus.DOING,
    "ready": TaskStatus.REVIEW,
    "approve": TaskStatus.DONE,
    "reject": TaskStatus.DOING,
    "block": TaskStatus.BLOCKED,
    "reopen": TaskStatus.TODO,
    "cancel": TaskStatus.CANCELLED,
}
#: `/done` is special: developers finish into review, reviewers finish into done.
DONE_COMMAND = "done"
#: Commands whose trailing text is stored as the reason (a comment on the task).
REASON_COMMANDS = frozenset({"reject", "block", "cancel"})

TASK_COMMANDS = ("task", "add")
LIST_COMMANDS = ("list", "my", "review", "digest", "find")
EDIT_COMMANDS = (
    "info", "history", "edit", "assign", "unassign", "comment", "delete", "restore",
)  # fmt: skip
ADMIN_COMMANDS = ("areas", "addarea", "delarea", "team", "role", "specialty")
PUBLIC_COMMANDS = ("start", "help", "chatid")
AI_COMMANDS = ("ai",)
QA_COMMANDS = ("bug", "bugs", "check", "release", "qa", "files", "apk", "app", "build")

ALL_COMMANDS: tuple[str, ...] = (
    *PUBLIC_COMMANDS,
    *TASK_COMMANDS,
    *LIST_COMMANDS,
    *EDIT_COMMANDS,
    *STATUS_COMMANDS,
    DONE_COMMAND,
    *ADMIN_COMMANDS,
    *QA_COMMANDS,
    *AI_COMMANDS,
)

# What appears in Telegram's "/" menu. Aliases and rarely used commands stay out of it.
_MENU_EVERYONE = (
    "task", "bug", "list", "my", "review", "bugs", "find", "info", "doing", "done",
    "check", "release", "apk", "ai", "digest", "specialty", "help",
)  # fmt: skip
_MENU_ADMINS = (
    "approve", "reject", "assign", "edit", "areas", "addarea", "team", "role", "qa",
)  # fmt: skip


def _commands(t: Translator, names: tuple[str, ...]) -> list[BotCommand]:
    return [BotCommand(command=name, description=t(f"menu.{name}")) for name in names]


async def publish_menus(bot: Bot, t: Translator) -> None:
    everyone = _commands(t, _MENU_EVERYONE)
    await bot.set_my_commands(everyone, scope=BotCommandScopeAllGroupChats())
    await bot.set_my_commands(everyone, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(
        everyone + _commands(t, _MENU_ADMINS), scope=BotCommandScopeAllChatAdministrators()
    )
