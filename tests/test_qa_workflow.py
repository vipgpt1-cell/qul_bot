"""The QA step and checklists in the pure workflow rules."""

from __future__ import annotations

from qul_bot.domain.enums import Role, TaskStatus
from qul_bot.domain.workflow import (
    Actor,
    TaskState,
    approve_target,
    check_transition,
    done_target,
)
from qul_bot.errors import AppError

S = TaskStatus
ADMIN = Actor(1, Role.ADMIN)
REVIEWER = Actor(2, Role.REVIEWER)
DEV = Actor(3, Role.MEMBER)
QA = Actor(4, Role.MEMBER, is_qa=True)


def state(status: TaskStatus, *, qa: bool = True, checks: int = 0, assignees=(3,)) -> TaskState:  # type: ignore[no-untyped-def]
    return TaskState(
        status, reporter_id=9, assignee_ids=assignees, qa_active=qa, open_checks=checks
    )


def code(task: TaskState, target: TaskStatus, actor: Actor) -> str | None:
    try:
        check_transition(task, target, actor)
    except AppError as error:
        return error.code
    return None


def test_targets_follow_the_qa_step() -> None:
    assert approve_target(S.REVIEW, qa_active=True) is S.TESTING
    assert approve_target(S.REVIEW, qa_active=False) is S.DONE
    assert approve_target(S.TESTING, qa_active=True) is S.DONE
    assert done_target(S.TESTING, qa_active=True) is S.DONE
    assert done_target(S.REVIEW, qa_active=True) is S.TESTING
    assert done_target(S.DOING, qa_active=True) is S.REVIEW


def test_review_goes_to_testing_when_qa_is_active() -> None:
    assert code(state(S.REVIEW), S.TESTING, REVIEWER) is None
    assert code(state(S.REVIEW), S.DONE, REVIEWER) == "qa_required"
    assert code(state(S.REVIEW), S.DONE, ADMIN) is None  # admins may skip testing
    assert code(state(S.REVIEW, qa=False), S.TESTING, REVIEWER) == "qa_inactive"
    assert code(state(S.REVIEW, qa=False), S.DONE, REVIEWER) is None


def test_only_testers_decide_in_testing() -> None:
    assert code(state(S.TESTING), S.DONE, QA) is None
    assert code(state(S.TESTING), S.DOING, QA) is None  # failed the test
    assert code(state(S.TESTING), S.DONE, DEV) == "tester_required"
    assert code(state(S.TESTING), S.DONE, REVIEWER) == "tester_required"
    assert code(state(S.TESTING), S.DONE, ADMIN) is None


def test_nobody_passes_their_own_work() -> None:
    own_qa = state(S.TESTING, assignees=(QA.user_id,))
    assert code(own_qa, S.DONE, QA) == "self_approval"
    own_review = state(S.REVIEW, assignees=(REVIEWER.user_id,))
    assert code(own_review, S.TESTING, REVIEWER) == "self_approval"


def test_open_checklist_blocks_done() -> None:
    assert code(state(S.TESTING, checks=2), S.DONE, QA) == "checklist_incomplete"
    assert code(state(S.REVIEW, qa=False, checks=1), S.DONE, REVIEWER) == "checklist_incomplete"
    assert code(state(S.TESTING, checks=2), S.DOING, QA) is None  # sending back is fine
