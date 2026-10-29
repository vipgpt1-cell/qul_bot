from __future__ import annotations

import pytest

from qul_bot.domain.enums import Priority, Role, TaskKind, TaskStatus
from qul_bot.domain.releases import normalize_release
from qul_bot.domain.specialty import Specialty
from qul_bot.domain.workflow import Actor
from qul_bot.errors import AppError, InputError, NotFoundError, PermissionDenied
from qul_bot.services.tasks import NewTask, TaskFilter, TaskPatch, TaskService
from qul_bot.services.workspaces import WorkspaceService
from tests.conftest import World

S = TaskStatus


async def make_qa(world: World) -> Actor:
    """Turn dev2 into the team's tester."""
    await WorkspaceService(world.session).set_specialty(
        world.workspace.id, world.dev2, Specialty.QA, world.admin.id, Role.ADMIN
    )
    return Actor(world.dev2.id, Role.MEMBER, is_qa=True)


async def new(world: World, title: str = "Work", **kwargs: object) -> int:
    task = await TaskService(world.session).create(
        world.workspace,
        world.dev,
        NewTask(title=title, **kwargs),  # type: ignore[arg-type]
    )
    return task.id


async def test_qa_step_needs_a_tester_and_the_setting(world: World) -> None:
    service = TaskService(world.session)
    assert not await service.qa_active(world.workspace.id)  # nobody is QA yet
    await make_qa(world)
    assert await service.qa_active(world.workspace.id)
    await WorkspaceService(world.session).configure_qa(world.workspace, enabled=False)
    assert not await service.qa_active(world.workspace.id)


async def test_full_flow_through_testing(world: World) -> None:
    service = TaskService(world.session)
    qa = await make_qa(world)
    task_id = await new(world, assignee_usernames=["devalisher"])
    await service.change_status(task_id, world.dev_actor, S.REVIEW)
    with pytest.raises(AppError) as skipped:
        await service.change_status(task_id, world.reviewer_actor, S.DONE)
    assert skipped.value.code == "qa_required"
    await service.change_status(task_id, world.reviewer_actor, S.TESTING)
    with pytest.raises(PermissionDenied):
        await service.change_status(task_id, world.dev_actor, S.DONE)
    done = await service.change_status(task_id, qa, S.DONE)
    assert done.task.status is S.DONE


async def test_checklist_add_toggle_remove_and_block_done(world: World) -> None:
    service = TaskService(world.session)
    qa = await make_qa(world)
    task_id = await new(world, assignee_usernames=["devalisher"])
    items = await service.add_checks(
        task_id, world.dev_actor, ["Login", " ", "Dark mode", "Logout"]
    )
    assert [i.text for i in items] == ["Login", "Dark mode", "Logout"]
    assert await service.checklist_progress(task_id) == (0, 3)

    removed = await service.remove_check(task_id, world.dev_actor, 3)
    assert removed.text == "Logout"
    with pytest.raises(NotFoundError):
        await service.remove_check(task_id, world.dev_actor, 7)

    await service.change_status(task_id, world.dev_actor, S.REVIEW)
    await service.change_status(task_id, world.reviewer_actor, S.TESTING)
    with pytest.raises(AppError) as blocked:
        await service.change_status(task_id, qa, S.DONE)
    assert blocked.value.code == "checklist_incomplete"
    assert blocked.value.params == {"count": 2}

    for item in await service.checklist(task_id):
        await service.toggle_check(item.id, qa)  # testers may tick on any task
    assert await service.checklist_progress(task_id) == (2, 2)
    _, untoggled = await service.toggle_check(items[0].id, qa)
    assert not untoggled.done
    await service.toggle_check(items[0].id, qa)
    assert (await service.change_status(task_id, qa, S.DONE)).task.status is S.DONE


async def test_checklist_rights_and_limits(world: World) -> None:
    service = TaskService(world.session)
    task_id = await new(world, assignee_usernames=["devalisher"])
    stranger = Actor(world.dev2.id, Role.MEMBER)  # not involved, not QA
    with pytest.raises(PermissionDenied):
        await service.add_checks(task_id, stranger, ["x"])
    with pytest.raises(InputError):
        await service.add_checks(task_id, world.dev_actor, ["", "  "])
    await service.add_checks(task_id, world.dev_actor, [f"item {i}" for i in range(30)])
    with pytest.raises(InputError) as full:
        await service.add_checks(task_id, world.dev_actor, ["one too many"])
    assert full.value.code == "checklist_full"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1.4.0", "1.4.0"), ("v1.4.0", "1.4.0"), ("V2.0", "2.0"), ("2026-10", "2026-10"),
     ("beta", "beta"), ("RC1", "rc1")],
)  # fmt: skip
def test_release_labels(raw: str, expected: str) -> None:
    assert normalize_release(raw) == expected


@pytest.mark.parametrize("raw", ["", " ", "has space", "x" * 40, "-1.0"])
def test_bad_release_labels(raw: str) -> None:
    with pytest.raises(InputError):
        normalize_release(raw)


async def test_release_report_and_listing(world: World) -> None:
    service = TaskService(world.session)
    a = await new(world, "Feature A", release="v1.4.0", assignee_usernames=["devalisher"])
    await new(world, "Crash", release="1.4.0", kind=TaskKind.BUG, priority=Priority.URGENT)
    await new(world, "Next", release="1.10.0")
    await new(world, "Old", release="1.9.0")

    assert [r for r, _, _ in await service.releases(world.workspace.id)] == [
        "1.10.0", "1.9.0", "1.4.0",
    ]  # fmt: skip
    report = await service.release_report(world.workspace.id, "v1.4.0")
    assert (report.release, len(report.tasks), report.ready) == ("1.4.0", 2, False)
    assert [t.title for t in report.open_bugs] == ["Crash"]

    await service.change_status(a, world.dev_actor, S.REVIEW)
    await service.change_status(a, world.reviewer_actor, S.DONE)
    crash = report.open_bugs[0]
    await service.change_status(crash.id, world.admin_actor, S.CANCELLED)
    assert (await service.release_report(world.workspace.id, "1.4.0")).ready

    with pytest.raises(NotFoundError):
        await service.release_report(world.workspace.id, "9.9.9")


async def test_release_can_be_set_and_cleared_by_edit(world: World) -> None:
    service = TaskService(world.session)
    task_id = await new(world)
    assert (await service.edit(task_id, world.dev_actor, TaskPatch(release="v2.0"))) == {
        "release": [None, "2.0"]
    }
    assert "release" in await service.edit(task_id, world.dev_actor, TaskPatch(clear_release=True))


async def test_bugs_filter_attachments_and_testing_digest(world: World) -> None:
    from datetime import date

    service = TaskService(world.session)
    await make_qa(world)
    bug = await new(world, "Bug", kind=TaskKind.BUG, assignee_usernames=["devalisher"])
    await new(world, "Plain task")
    bugs = await service.list_tasks(TaskFilter(workspace_id=world.workspace.id, kind=TaskKind.BUG))
    assert [t.id for t in bugs.items] == [bug]

    await service.add_attachment(bug, world.dev.id, "photo", "FILE123", None)
    assert [a.file_id for a in await service.attachments(bug)] == ["FILE123"]

    await service.change_status(bug, world.dev_actor, S.REVIEW)
    await service.change_status(bug, world.reviewer_actor, S.TESTING)
    digest = await service.digest(world.workspace.id, date(2026, 10, 29))
    assert [t.id for t in digest.in_testing] == [bug]
    assert bug not in [t.id for t in digest.unassigned]
