from __future__ import annotations

import pytest

from qul_bot.domain.enums import Role, TaskStatus
from qul_bot.domain.workflow import (
    TRANSITIONS,
    Actor,
    TaskState,
    can_delete,
    can_modify,
    check_transition,
    done_target,
)
from qul_bot.errors import AppError, PermissionDenied, WorkflowError

S = TaskStatus
ADMIN = Actor(1, Role.ADMIN)
REVIEWER = Actor(2, Role.REVIEWER)
DEV = Actor(3, Role.MEMBER)
OTHER = Actor(4, Role.MEMBER)


def task(status: TaskStatus, assignees: tuple[int, ...] = (3,), reporter: int = 4) -> TaskState:
    return TaskState(status=status, reporter_id=reporter, assignee_ids=assignees)


def code(task_state: TaskState, target: TaskStatus, actor: Actor) -> str | None:
    try:
        check_transition(task_state, target, actor)
    except AppError as error:
        return error.code
    return None


def test_developer_flow_ends_in_review_not_done() -> None:
    assert code(task(S.TODO), S.DOING, DEV) is None
    assert code(task(S.DOING), S.REVIEW, DEV) is None
    assert code(task(S.REVIEW), S.DONE, DEV) == "approver_required"
    assert code(task(S.DOING), S.DONE, DEV) == "invalid_transition"


def test_reviewer_approves_or_rejects() -> None:
    assert code(task(S.REVIEW), S.DONE, REVIEWER) is None
    assert code(task(S.REVIEW), S.DOING, REVIEWER) is None


def test_developer_cannot_pull_task_out_of_review_or_done() -> None:
    assert code(task(S.REVIEW), S.DOING, DEV) == "approver_required"
    assert code(task(S.DONE), S.TODO, DEV) == "approver_required"
    assert code(task(S.REVIEW), S.CANCELLED, DEV) == "approver_required"


def test_reviewer_who_is_assignee_cannot_self_approve() -> None:
    own = task(S.REVIEW, assignees=(REVIEWER.user_id,))
    assert code(own, S.DONE, REVIEWER) == "self_approval"
    assert code(own, S.DOING, REVIEWER) is None  # sending it back is fine


def test_admin_may_approve_own_task() -> None:
    assert code(task(S.REVIEW, assignees=(ADMIN.user_id,)), S.DONE, ADMIN) is None


def test_uninvolved_member_cannot_touch_assigned_task() -> None:
    assert code(task(S.TODO), S.DOING, Actor(99, Role.MEMBER)) == "not_involved"


def test_anyone_may_pick_up_an_unassigned_task() -> None:
    assert code(task(S.TODO, assignees=()), S.DOING, Actor(99, Role.MEMBER)) is None


def test_reporter_may_cancel_their_task() -> None:
    assert code(task(S.TODO, reporter=OTHER.user_id), S.CANCELLED, OTHER) is None


def test_same_status_and_invalid_transitions() -> None:
    assert code(task(S.TODO), S.TODO, ADMIN) == "same_status"
    assert code(task(S.TODO), S.DONE, ADMIN) == "invalid_transition"
    assert code(task(S.BLOCKED), S.REVIEW, ADMIN) == "invalid_transition"


def test_reopen() -> None:
    assert code(task(S.DONE), S.TODO, REVIEWER) is None
    assert code(task(S.CANCELLED), S.TODO, DEV) is None


def test_every_status_has_an_exit_and_targets_are_valid() -> None:
    assert set(TRANSITIONS) == set(TaskStatus)
    for source, targets in TRANSITIONS.items():
        assert targets, f"{source} is a dead end"
        assert source not in targets


def test_done_target() -> None:
    assert done_target(S.REVIEW) is S.DONE
    for status in (S.TODO, S.DOING, S.BLOCKED):
        assert done_target(status) is S.REVIEW


def test_can_modify_and_delete() -> None:
    state = task(S.TODO, assignees=(3,), reporter=4)
    assert can_modify(state, ADMIN)
    assert can_modify(state, DEV)  # assignee
    assert can_modify(state, OTHER)  # reporter
    assert not can_modify(state, Actor(99, Role.MEMBER))
    assert can_delete(state, ADMIN)
    assert can_delete(state, OTHER)  # reporter
    assert not can_delete(state, DEV)
    assert not can_delete(state, REVIEWER)


def test_error_types() -> None:
    with pytest.raises(WorkflowError):
        check_transition(task(S.TODO), S.TODO, ADMIN)
    with pytest.raises(PermissionDenied):
        check_transition(task(S.REVIEW), S.DONE, DEV)
