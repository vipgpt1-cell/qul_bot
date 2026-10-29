from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from qul_bot.bot.callbacks import (
    ACTION_ASSIGN,
    ACTION_CHECKS,
    ACTION_DELETE_NO,
    ACTION_DELETE_YES,
    ACTION_ME,
    ACTION_PRIORITY,
    AssignPick,
    BugSeverity,
    CheckToggle,
    HelpPage,
    SpecialtyPick,
    TaskAction,
    encode_filter,
)
from qul_bot.bot.formatting import group_by_specialty, specialty_label, truncate
from qul_bot.db.models import ChecklistItem, Membership, Task
from qul_bot.domain.enums import TaskStatus
from qul_bot.domain.specialty import SPECIALTY_ORDER, Specialty, to_code
from qul_bot.i18n import Translator
from qul_bot.services.tasks import TaskFilter

S = TaskStatus

# Buttons per status: (action, i18n key). Permissions are checked when a button is pressed;
# the card is shared by everyone in the chat, so it cannot be tailored to one viewer.
_PRIMARY: dict[TaskStatus, list[tuple[str, str]]] = {
    S.TODO: [("start", "btn.start"), ("ready", "btn.ready")],
    S.DOING: [("ready", "btn.ready"), ("block", "btn.block")],
    S.REVIEW: [("approve", "btn.approve"), ("reject", "btn.reject")],
    S.TESTING: [("approve", "btn.test_pass"), ("reject", "btn.test_fail")],
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
        rows.append(
            [
                button(ACTION_ME, "btn.me"),
                button(ACTION_ASSIGN, "btn.assign"),
                button(ACTION_PRIORITY, "btn.priority"),
            ]
        )
    if task.status not in (S.DONE, S.CANCELLED):
        rows.append([button(ACTION_CHECKS, "btn.checklist")])
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


def _pairs(buttons: list[InlineKeyboardButton]) -> list[list[InlineKeyboardButton]]:
    return [buttons[i : i + 2] for i in range(0, len(buttons), 2)]


def _pick(task: Task, step: str, *, group: int = 0, user: int = 0) -> str:
    return AssignPick(task_id=task.id, step=step, group=group, user=user).pack()


def assign_menu_keyboard(
    t: Translator, task: Task, members: list[Membership]
) -> InlineKeyboardMarkup:
    """Step 1 of the picker: which part of the team?"""
    groups = [
        InlineKeyboardButton(
            text=f"{specialty_label(t, specialty)} ({len(people)})",
            callback_data=_pick(task, "group", group=to_code(specialty)),
        )
        for specialty, people in group_by_specialty(members)
    ]
    done = InlineKeyboardButton(text=t("btn.picker_done"), callback_data=_pick(task, "close"))
    return InlineKeyboardMarkup(inline_keyboard=[*_pairs(groups), [done]])


def assign_group_keyboard(
    t: Translator, task: Task, people: list[Membership], group: Specialty | None
) -> InlineKeyboardMarkup:
    """Step 2: people of one specialty; pressing a name toggles the assignment."""
    assigned = {u.id for u in task.assignees}
    names = [
        InlineKeyboardButton(
            text=f"{'✅ ' if m.user_id in assigned else ''}{truncate(m.user.display_name, 24)}",
            callback_data=_pick(task, "user", group=to_code(group), user=m.user_id),
        )
        for m in people
    ]
    controls = [
        InlineKeyboardButton(text=t("btn.back"), callback_data=_pick(task, "menu")),
        InlineKeyboardButton(text=t("btn.picker_done"), callback_data=_pick(task, "close")),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[*_pairs(names), controls])


def specialty_keyboard(t: Translator) -> InlineKeyboardMarkup:
    """Choose your own specialty."""
    buttons = [
        InlineKeyboardButton(
            text=specialty_label(t, specialty),
            callback_data=SpecialtyPick(code=to_code(specialty)).pack(),
        )
        for specialty in SPECIALTY_ORDER
    ]
    clear = InlineKeyboardButton(
        text=t("btn.specialty_clear"), callback_data=SpecialtyPick(code=0).pack()
    )
    return InlineKeyboardMarkup(inline_keyboard=[*_pairs(buttons), [clear]])


HELP_PAGES = ("create", "workflow", "view", "team", "qa", "ai")


def help_keyboard(t: Translator) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=t(f"help.btn.{page}"), callback_data=HelpPage(page=page).pack())
        for page in HELP_PAGES
    ]
    return InlineKeyboardMarkup(inline_keyboard=_pairs(buttons))


def help_back_keyboard(t: Translator) -> InlineKeyboardMarkup:
    back = InlineKeyboardButton(text=t("btn.back"), callback_data=HelpPage(page="main").pack())
    return InlineKeyboardMarkup(inline_keyboard=[[back]])


BUG_SEVERITIES = ("critical", "major", "minor", "trivial")


def severity_keyboard(t: Translator) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=t(f"bug.severity.{level}"), callback_data=BugSeverity(level=level).pack()
        )
        for level in BUG_SEVERITIES
    ]
    return InlineKeyboardMarkup(inline_keyboard=_pairs(buttons))


def checklist_keyboard(items: list[ChecklistItem]) -> InlineKeyboardMarkup | None:
    if not items:
        return None
    rows = [
        [
            InlineKeyboardButton(
                text=f"{'✅' if item.done else '⬜'} {n}. {truncate(item.text, 40)}",
                callback_data=CheckToggle(item_id=item.id).pack(),
            )
        ]
        for n, item in enumerate(items, 1)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
