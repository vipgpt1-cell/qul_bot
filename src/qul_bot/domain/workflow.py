"""The task workflow: which status changes exist and who may perform them.

    todo ─► doing ─► review ─► [testing] ─► done
      │       │         │          │          │
      │       ▼         └─► doing ◄┘ (sent back)
      └────► blocked                  done ─► todo (reopen)

Rules
-----
* Anyone involved in a task (assignee, reporter, reviewer/admin, or anyone if it has no
  assignee yet) may move it forward: todo → doing → review.
* Only a reviewer or admin may take a task *out of* review or done: approve it,
  send it back, or reopen it.
* The QA step (testing) is active when the workspace has it enabled *and* the team has at
  least one QA. Then an approved review goes to testing, and only a QA or an admin may move
  a task out of testing.
* Nobody approves their own work (review or testing), unless they are an admin.
* A task with unchecked checklist items cannot be done.
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
    S.REVIEW: frozenset({S.DONE, S.TESTING, S.DOING, S.CANCELLED}),
    S.TESTING: frozenset({S.DONE, S.DOING, S.CANCELLED}),
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
    #: Has the QA specialty: may pass or fail tasks in testing.
    is_qa: bool = False

    @property
    def can_approve(self) -> bool:
        return self.role in (Role.ADMIN, Role.REVIEWER)

    @property
    def can_test(self) -> bool:
        return self.is_qa or self.role is Role.ADMIN


@dataclass(frozen=True, slots=True)
class TaskState:
    status: TaskStatus
    reporter_id: int
    assignee_ids: Collection[int]
    #: Is the QA step in force for this task's workspace?
    qa_active: bool = False
    #: Checklist items not ticked yet.
    open_checks: int = 0


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


def approve_target(status: TaskStatus, qa_active: bool) -> TaskStatus:
    """Where approving leads: review goes to testing when QA is active, otherwise to done."""
    return S.TESTING if status is S.REVIEW and qa_active else S.DONE


def done_target(status: TaskStatus, qa_active: bool = False) -> TaskStatus:
    """Where `/done` leads: developers finish into review; reviewers and QA approve."""
    if status in (S.REVIEW, S.TESTING):
        return approve_target(status, qa_active)
    return S.REVIEW


def check_transition(task: TaskState, target: TaskStatus, actor: Actor) -> None:
    """Raise unless `actor` may move `task` to `target`."""
    if target is task.status:
        raise WorkflowError("same_status", status=task.status.value)
    if target not in TRANSITIONS[task.status]:
        raise WorkflowError("invalid_transition", source=task.status.value, target=target.value)

    if task.status is S.TESTING:
        if not actor.can_test:
            raise PermissionDenied("tester_required")
    elif task.status in APPROVER_ONLY_SOURCES:
        if not actor.can_approve:
            raise PermissionDenied("approver_required")
    elif not can_modify(task, actor):
        raise PermissionDenied("not_involved")

    if target is S.TESTING and not task.qa_active:
        raise WorkflowError("qa_inactive")
    if (
        task.status is S.REVIEW
        and target is S.DONE
        and task.qa_active
        and actor.role is not Role.ADMIN
    ):
        raise WorkflowError("qa_required")
    approving = target is S.DONE or (target is S.TESTING and task.status is S.REVIEW)
    if approving and actor.user_id in task.assignee_ids and actor.role is not Role.ADMIN:
        raise PermissionDenied("self_approval")
    if target is S.DONE and task.open_checks:
        raise WorkflowError("checklist_incomplete", count=task.open_checks)
