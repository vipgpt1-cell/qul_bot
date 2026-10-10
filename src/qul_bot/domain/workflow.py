"""The task workflow: which status changes exist and who may perform them.

    todo ─► doing ─► review ─► done
      │       │         │        │
      │       ▼         └─► doing (rejected)
      └────► blocked          done ─► todo (reopen)

Rules
-----
* Anyone involved in a task (assignee, reporter, reviewer/admin, or anyone if it has no
  assignee yet) may move it forward: todo → doing → review.
* Only a reviewer or admin may take a task *out of* review or done: approve it,
  send it back, or reopen it.
* An assignee cannot approve their own task, unless they are an admin.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from qul_bot.domain.enums import Role, TaskStatus
from qul_bot.errors import PermissionDenied, WorkflowError

S = TaskStatus

TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    S.TODO: frozenset({S.DOING, S.REVIEW, S.BLOCKED, S.CANCELLED}),
    S.DOING: frozenset({S.TODO, S.REVIEW, S.BLOCKED, S.CANCELLED}),
    S.BLOCKED: frozenset({S.TODO, S.DOING, S.CANCELLED}),
    S.REVIEW: frozenset({S.DONE, S.DOING, S.CANCELLED}),
    S.DONE: frozenset({S.TODO}),
    S.CANCELLED: frozenset({S.TODO}),
}

#: Leaving these statuses is a reviewer decision.
APPROVER_ONLY_SOURCES = frozenset({S.REVIEW, S.DONE})
#: Moving into these statuses when nobody is assigned makes the actor the assignee.
AUTO_ASSIGN_TARGETS = frozenset({S.DOING, S.REVIEW})


@dataclass(frozen=True, slots=True)
class Actor:
    user_id: int
    role: Role

    @property
    def can_approve(self) -> bool:
        return self.role in (Role.ADMIN, Role.REVIEWER)


@dataclass(frozen=True, slots=True)
class TaskState:
    status: TaskStatus
    reporter_id: int
    assignee_ids: Collection[int]


def can_modify(task: TaskState, actor: Actor) -> bool:
    """May this actor change the task at all (status, fields, assignees)?"""
    return (
        actor.can_approve
        or actor.user_id == task.reporter_id
        or actor.user_id in task.assignee_ids
        or not task.assignee_ids
    )


def can_delete(task: TaskState, actor: Actor) -> bool:
    """Only admins and the person who created a task may delete it."""
    return actor.role is Role.ADMIN or actor.user_id == task.reporter_id


def done_target(status: TaskStatus) -> TaskStatus:
    """Where `/done` leads: developers finish into review, reviewers finish into done."""
    return S.DONE if status is S.REVIEW else S.REVIEW


def check_transition(task: TaskState, target: TaskStatus, actor: Actor) -> None:
    """Raise unless `actor` may move `task` to `target`."""
    if target is task.status:
        raise WorkflowError("same_status", status=task.status.value)
    if target not in TRANSITIONS[task.status]:
        raise WorkflowError("invalid_transition", source=task.status.value, target=target.value)
    if task.status in APPROVER_ONLY_SOURCES and not actor.can_approve:
        raise PermissionDenied("approver_required")
    if not can_modify(task, actor):
        raise PermissionDenied("not_involved")
    if target is S.DONE and actor.user_id in task.assignee_ids and actor.role is not Role.ADMIN:
        raise PermissionDenied("self_approval")
