from __future__ import annotations

from aiogram.filters.callback_data import CallbackData

from qul_bot.domain.enums import PRIORITY_ORDER, Priority, TaskKind, TaskStatus
from qul_bot.services.tasks import TaskFilter


class TaskAction(CallbackData, prefix="ta"):
    """A button on a task card. `action` is one of the `ACTION_*` names below."""

    action: str
    task_id: int


# Button actions that move a task to a new status.
# Button actions that change the status, and the command each one behaves like.
ACTION_TARGETS: dict[str, str] = {
    "start": "doing",
    "ready": "ready",
    "approve": "approve",
    "reject": "reject",
    "block": "block",
    "reopen": "reopen",
    "cancel": "cancel",
}
ACTION_ME = "me"
ACTION_ASSIGN = "assign"
ACTION_CHECKS = (
    "checks"  # posts the task's test checklist  # opens the "pick people by specialty" view
)
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
    kind: int = 0


#: Bit order for statuses in callback data. Follows declaration order, which only ever grows
#: at the end, so buttons on old messages keep meaning the same thing.
_STATUS_BITS: tuple[TaskStatus, ...] = tuple(TaskStatus)
_KINDS: tuple[TaskKind, ...] = tuple(TaskKind)


def encode_filter(flt: TaskFilter, page: int) -> ListPage:
    return ListPage(
        ws=flt.workspace_id,
        page=page,
        area=flt.area_id or 0,
        st=sum(1 << i for i, s in enumerate(_STATUS_BITS) if s in flt.statuses),
        pr=PRIORITY_ORDER.index(flt.priority) + 1 if flt.priority else 0,
        user=flt.assignee_id or 0,
        closed=int(flt.include_closed),
        kind=_KINDS.index(flt.kind) + 1 if flt.kind else 0,
    )


def decode_filter(data: ListPage) -> tuple[TaskFilter, int]:
    priority: Priority | None = PRIORITY_ORDER[data.pr - 1] if 0 < data.pr <= 4 else None
    flt = TaskFilter(
        workspace_id=data.ws,
        area_id=data.area or None,
        statuses=frozenset(s for i, s in enumerate(_STATUS_BITS) if data.st & (1 << i)),
        priority=priority,
        assignee_id=data.user or None,
        include_closed=bool(data.closed),
        kind=_KINDS[data.kind - 1] if 0 < data.kind <= len(_KINDS) else None,
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


class CheckToggle(CallbackData, prefix="ck"):
    """Tick or untick one checklist item."""

    item_id: int


class BugSeverity(CallbackData, prefix="bs"):
    """Severity chosen in the /bug form."""

    level: str  # critical | major | minor | trivial
