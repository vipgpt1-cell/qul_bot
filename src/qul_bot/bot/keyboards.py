from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from qul_bot.bot.callbacks import (
    ACTION_DELETE_NO,
    ACTION_DELETE_YES,
    ACTION_ME,
    ACTION_PRIORITY,
    TaskAction,
    encode_filter,
)
from qul_bot.db.models import Task
from qul_bot.domain.enums import TaskStatus
from qul_bot.i18n import Translator
from qul_bot.services.tasks import TaskFilter

S = TaskStatus

# Buttons per status: (action, i18n key). Permissions are checked when a button is pressed;
# the card is shared by everyone in the chat, so it cannot be tailored to one viewer.
_PRIMARY: dict[TaskStatus, list[tuple[str, str]]] = {
    S.TODO: [("start", "btn.start"), ("ready", "btn.ready")],
    S.DOING: [("ready", "btn.ready"), ("block", "btn.block")],
    S.REVIEW: [("approve", "btn.approve"), ("reject", "btn.reject")],
    S.BLOCKED: [("start", "btn.resume"), ("cancel", "btn.cancel")],
    S.DONE: [("reopen", "btn.reopen")],
    S.CANCELLED: [("reopen", "btn.reopen")],
}
_SECONDARY_STATUSES = (S.TODO, S.DOING, S.BLOCKED)


def task_keyboard(t: Translator, task: Task) -> InlineKeyboardMarkup:
    def button(action: str, key: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=t(key), callback_data=TaskAction(action=action, task_id=task.id).pack()
        )

    rows = [[button(action, key) for action, key in _PRIMARY[task.status]]]
    if task.status in _SECONDARY_STATUSES:
        rows.append([button(ACTION_ME, "btn.me"), button(ACTION_PRIORITY, "btn.priority")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_delete_keyboard(t: Translator, task: Task) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn.delete_yes"),
                    callback_data=TaskAction(action=ACTION_DELETE_YES, task_id=task.id).pack(),
                ),
                InlineKeyboardButton(
                    text=t("btn.delete_no"),
                    callback_data=TaskAction(action=ACTION_DELETE_NO, task_id=task.id).pack(),
                ),
            ]
        ]
    )


def pagination_keyboard(flt: TaskFilter, page: int, pages: int) -> InlineKeyboardMarkup | None:
    if pages <= 1:
        return None
    row: list[InlineKeyboardButton] = []
    if page > 0:
        row.append(
            InlineKeyboardButton(text="◀️", callback_data=encode_filter(flt, page - 1).pack())
        )
    row.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="noop"))
    if page < pages - 1:
        row.append(
            InlineKeyboardButton(text="▶️", callback_data=encode_filter(flt, page + 1).pack())
        )
    return InlineKeyboardMarkup(inline_keyboard=[row])
