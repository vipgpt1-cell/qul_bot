from __future__ import annotations

from aiogram.filters.callback_data import CallbackData

from qul_bot.domain.enums import PRIORITY_ORDER, STATUS_ORDER, Priority, TaskStatus
from qul_bot.services.tasks import TaskFilter


class TaskAction(CallbackData, prefix="ta"):
    """A button on a task card. `action` is one of the `ACTION_*` names below."""

    action: str
    task_id: int


# Button actions that move a task to a new status.
ACTION_TARGETS: dict[str, TaskStatus] = {
    "start": TaskStatus.DOING,
    "ready": TaskStatus.REVIEW,
    "approve": TaskStatus.DONE,
    "reject": TaskStatus.DOING,
    "block": TaskStatus.BLOCKED,
    "reopen": TaskStatus.TODO,
    "cancel": TaskStatus.CANCELLED,
}
ACTION_ME = "me"
ACTION_ASSIGN = "assign"  # opens the "pick people by specialty" view
ACTION_PRIORITY = "prio"
ACTION_DELETE_YES = "delyes"
ACTION_DELETE_NO = "delno"


class ListPage(CallbackData, prefix="lp"):
    """Pagination button of a task list; carries the whole filter (callback data is stateless)."""

    ws: int
    page: int
    area: int = 0
    st: int = 0
    pr: int = 0
    user: int = 0
    closed: int = 0


def encode_filter(flt: TaskFilter, page: int) -> ListPage:
    return ListPage(
        ws=flt.workspace_id,
        page=page,
        area=flt.area_id or 0,
        st=sum(1 << i for i, s in enumerate(STATUS_ORDER) if s in flt.statuses),
        pr=PRIORITY_ORDER.index(flt.priority) + 1 if flt.priority else 0,
        user=flt.assignee_id or 0,
        closed=int(flt.include_closed),
    )


def decode_filter(data: ListPage) -> tuple[TaskFilter, int]:
    priority: Priority | None = PRIORITY_ORDER[data.pr - 1] if 0 < data.pr <= 4 else None
    flt = TaskFilter(
        workspace_id=data.ws,
        area_id=data.area or None,
        statuses=frozenset(s for i, s in enumerate(STATUS_ORDER) if data.st & (1 << i)),
        priority=priority,
        assignee_id=data.user or None,
        include_closed=bool(data.closed),
    )
    return flt, data.page


class AssignPick(CallbackData, prefix="ap"):
    """A button in the assignee picker. `group` is a `domain.specialty` code (0 = none)."""

    task_id: int
    step: str  # "group" | "user" | "menu" | "close"
    group: int = 0
    user: int = 0


class SpecialtyPick(CallbackData, prefix="sp"):
    """Choosing your own specialty. `code` 0 clears it."""

    code: int


class HelpPage(CallbackData, prefix="hp"):
    """A section of the help menu (`main` returns to the menu)."""

    page: str
