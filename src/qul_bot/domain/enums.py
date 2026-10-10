from __future__ import annotations

from enum import StrEnum


class TaskStatus(StrEnum):
    TODO = "todo"
    DOING = "doing"
    REVIEW = "review"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"


#: Statuses that still need attention.
ACTIVE_STATUSES: tuple[TaskStatus, ...] = (
    TaskStatus.TODO,
    TaskStatus.DOING,
    TaskStatus.REVIEW,
    TaskStatus.BLOCKED,
)
CLOSED_STATUSES: tuple[TaskStatus, ...] = (TaskStatus.DONE, TaskStatus.CANCELLED)

#: Display order in lists: what is being worked on first, finished work last.
STATUS_ORDER: tuple[TaskStatus, ...] = (
    TaskStatus.DOING,
    TaskStatus.REVIEW,
    TaskStatus.BLOCKED,
    TaskStatus.TODO,
    TaskStatus.DONE,
    TaskStatus.CANCELLED,
)


class Priority(StrEnum):
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


#: Most urgent first.
PRIORITY_ORDER: tuple[Priority, ...] = (
    Priority.URGENT,
    Priority.HIGH,
    Priority.NORMAL,
    Priority.LOW,
)


class Role(StrEnum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    MEMBER = "member"


class EventType(StrEnum):
    """Kinds of entries in the task event log (also the future integration feed)."""

    CREATED = "task.created"
    STATUS_CHANGED = "task.status_changed"
    ASSIGNED = "task.assigned"
    UNASSIGNED = "task.unassigned"
    EDITED = "task.edited"
    COMMENTED = "task.commented"
    DELETED = "task.deleted"
    RESTORED = "task.restored"
