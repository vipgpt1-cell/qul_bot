from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from qul_bot.db.models import TaskEvent
from qul_bot.domain.enums import EventType, Priority, Role, TaskStatus
from qul_bot.errors import AppError, InputError, NotFoundError, PermissionDenied
from qul_bot.services.tasks import NewTask, TaskFilter, TaskPatch, TaskService
from qul_bot.services.workspaces import WorkspaceService
from tests.conftest import World

S = TaskStatus


async def create(world: World, title: str = "Fix crash", **kwargs: object) -> int:
    task = await TaskService(world.session).create(
        world.workspace,
        world.dev,
        NewTask(title=title, **kwargs),  # type: ignore[arg-type]
    )
    return task.id


async def events(world: World, task_id: int) -> list[EventType]:
    result = await world.session.execute(
        select(TaskEvent.type).where(TaskEvent.task_id == task_id).order_by(TaskEvent.id)
    )
    return list(result.scalars().all())


# ---- creating -------------------------------------------------------------------------


async def test_numbers_are_sequential_per_workspace(world: World) -> None:
    service = TaskService(world.session)
    first = await service.create(world.workspace, world.dev, NewTask(title="one"))
    second = await service.create(world.workspace, world.dev, NewTask(title="two"))
    assert (first.number, second.number) == (1, 2)
    assert first.status is S.TODO
    assert first.priority is Priority.NORMAL
    assert first.reporter_id == world.dev.id


async def test_create_resolves_area_and_assignees(world: World) -> None:
    workspaces = WorkspaceService(world.session)
    await workspaces.add_area(world.workspace.id, "mobile", "Mobil ilova")
    task = await TaskService(world.session).create(
        world.workspace,
        world.dev,
        NewTask(
            title="Login",
            area_slug="mobile",
            priority=Priority.HIGH,
            assignee_usernames=["devvalijon", "DevAlisher"],
            due=date(2026, 12, 1),
            description="steps",
        ),
    )
    assert task.area is not None
    assert task.area.slug == "mobile"
    assert {u.id for u in task.assignees} == {world.dev.id, world.dev2.id}
    assert task.due_date == date(2026, 12, 1)
    assert task.description == "steps"
    assert await events(world, task.id) == [EventType.CREATED]


async def test_create_rejects_unknown_area_user_and_empty_title(world: World) -> None:
    service = TaskService(world.session)
    with pytest.raises(NotFoundError) as unknown_area:
        await service.create(world.workspace, world.dev, NewTask(title="x", area_slug="nope"))
    assert unknown_area.value.code == "unknown_area"
    with pytest.raises(NotFoundError) as unknown_user:
        await service.create(
            world.workspace, world.dev, NewTask(title="x", assignee_usernames=["ghost1"])
        )
    assert unknown_user.value.code == "unknown_user"
    with pytest.raises(InputError):
        await service.create(world.workspace, world.dev, NewTask(title="   "))


# ---- review workflow ------------------------------------------------------------------


async def test_full_review_cycle(world: World) -> None:
    service = TaskService(world.session)
    task_id = await create(world, assignee_usernames=["devalisher"])

    started = await service.change_status(task_id, world.dev_actor, S.DOING)
    assert started.task.status is S.DOING
    assert not started.auto_assigned

    ready = await service.change_status(task_id, world.dev_actor, S.REVIEW)
    assert ready.task.status is S.REVIEW

    with pytest.raises(PermissionDenied) as denied:
        await service.change_status(task_id, world.dev_actor, S.DONE)
    assert denied.value.code == "approver_required"

    rejected = await service.change_status(
        task_id, world.reviewer_actor, S.DOING, reason="Add a test"
    )
    assert rejected.previous is S.REVIEW
    comments = await service.recent_comments(task_id)
    assert [c.body for c in comments] == ["Add a test"]
    assert comments[0].author_id == world.reviewer.id

    await service.change_status(task_id, world.dev_actor, S.REVIEW)
    approved = await service.change_status(task_id, world.reviewer_actor, S.DONE)
    assert approved.task.status is S.DONE
    assert approved.task.completed_at is not None

    reopened = await service.change_status(task_id, world.reviewer_actor, S.TODO)
    assert reopened.task.completed_at is None


async def test_starting_an_unassigned_task_assigns_the_actor(world: World) -> None:
    service = TaskService(world.session)
    task_id = await create(world)
    change = await service.change_status(task_id, world.dev2_actor, S.DOING)
    assert change.auto_assigned
    assert [u.id for u in change.task.assignees] == [world.dev2.id]
    assert EventType.ASSIGNED in await events(world, task_id)


async def test_assignee_reviewer_cannot_approve_own_work(world: World) -> None:
    service = TaskService(world.session)
    task_id = await create(world, assignee_usernames=["reviewer1"])
    await service.change_status(task_id, world.reviewer_actor, S.REVIEW)
    with pytest.raises(PermissionDenied) as denied:
        await service.change_status(task_id, world.reviewer_actor, S.DONE)
    assert denied.value.code == "self_approval"
    # an admin can still unblock a one-person team
    done = await service.change_status(task_id, world.admin_actor, S.DONE)
    assert done.task.status is S.DONE


async def test_status_change_records_event_with_reason(world: World) -> None:
    service = TaskService(world.session)
    task_id = await create(world, assignee_usernames=["devalisher"])
    await service.change_status(task_id, world.dev_actor, S.BLOCKED, reason="waiting for API")
    result = await world.session.execute(
        select(TaskEvent).where(
            TaskEvent.task_id == task_id, TaskEvent.type == EventType.STATUS_CHANGED
        )
    )
    event = result.scalar_one()
    assert event.data == {"source": "todo", "target": "blocked", "reason": "waiting for API"}
    assert event.actor_id == world.dev.id


# ---- assignment & editing -------------------------------------------------------------


async def test_assign_and_unassign(world: World) -> None:
    service = TaskService(world.session)
    task_id = await create(world, assignee_usernames=["devalisher"])
    added = await service.assign(task_id, world.dev_actor, [world.dev, world.dev2])
    assert [u.id for u in added] == [world.dev2.id]  # dev was already assigned
    removed = await service.unassign(task_id, world.dev_actor, [world.dev2])
    assert [u.id for u in removed] == [world.dev2.id]
    assert await service.unassign(task_id, world.dev_actor, [world.dev2]) == []


async def test_strangers_cannot_edit_assigned_tasks(world: World) -> None:
    service = TaskService(world.session)
    task_id = await create(world, assignee_usernames=["devalisher"])
    stranger = world.dev2_actor
    with pytest.raises(PermissionDenied):
        await service.edit(task_id, stranger, TaskPatch(title="hijack"))
    with pytest.raises(PermissionDenied):
        await service.assign(task_id, stranger, [world.dev2])


async def test_edit_reports_only_real_changes(world: World) -> None:
    service = TaskService(world.session)
    await WorkspaceService(world.session).add_area(world.workspace.id, "backend", None)
    task_id = await create(world, "Old title", priority=Priority.LOW)

    changes = await service.edit(
        task_id,
        world.dev_actor,
        TaskPatch(
            title="New title",
            priority=Priority.LOW,  # unchanged
            area_slug="backend",
            due=date(2026, 12, 24),
        ),
    )
    assert set(changes) == {"title", "area", "due"}
    task = await service.get_by_id(task_id)
    assert (task.title, task.area.slug if task.area else None) == ("New title", "backend")

    cleared = await service.edit(
        task_id, world.dev_actor, TaskPatch(clear_area=True, clear_due=True)
    )
    assert set(cleared) == {"area", "due"}
    assert await service.edit(task_id, world.dev_actor, TaskPatch(clear_due=True)) == {}


async def test_comments(world: World) -> None:
    service = TaskService(world.session)
    task_id = await create(world)
    await service.comment(task_id, world.dev2_actor, "  looks good  ")
    comments = await service.recent_comments(task_id)
    assert [c.body for c in comments] == ["looks good"]
    with pytest.raises(InputError):
        await service.comment(task_id, world.dev_actor, "   ")
    with pytest.raises(InputError) as too_long:
        await service.comment(task_id, world.dev_actor, "x" * 2001)
    assert too_long.value.code == "comment_too_long"


# ---- deleting -------------------------------------------------------------------------


async def test_soft_delete_and_restore(world: World) -> None:
    service = TaskService(world.session)
    task_id = await create(world)  # reporter: dev
    number = (await service.get_by_id(task_id)).number

    with pytest.raises(PermissionDenied):
        await service.soft_delete(task_id, world.dev2_actor)
    await service.soft_delete(task_id, world.dev_actor)

    with pytest.raises(NotFoundError):
        await service.get(world.workspace.id, number)
    with pytest.raises(PermissionDenied):
        await service.restore(world.workspace.id, number, world.dev_actor)
    restored = await service.restore(world.workspace.id, number, world.admin_actor)
    assert restored.deleted_at is None
    with pytest.raises(InputError):
        await service.restore(world.workspace.id, number, world.admin_actor)

    again = await service.create(world.workspace, world.dev, NewTask(title="next"))
    assert again.number == number + 1  # numbers are never reused


# ---- listing --------------------------------------------------------------------------


async def test_list_orders_by_status_then_priority_then_due(world: World) -> None:
    service = TaskService(world.session)
    low = await create(world, "low", priority=Priority.LOW)
    urgent = await create(world, "urgent", priority=Priority.URGENT)
    soon = await create(world, "soon", due=date(2026, 11, 1))
    later = await create(world, "later", due=date(2026, 12, 1))
    started = await create(world, "started")
    await service.change_status(started, world.dev_actor, S.DOING)

    page = await service.list_tasks(TaskFilter(workspace_id=world.workspace.id))
    assert [t.title for t in page.items] == ["started", "urgent", "soon", "later", "low"]
    assert page.total == 5
    assert {low, urgent, soon, later, started} == {t.id for t in page.items}


async def test_list_hides_closed_and_deleted_by_default(world: World) -> None:
    service = TaskService(world.session)
    open_id = await create(world, "open")
    done_id = await create(world, "done", assignee_usernames=["devalisher"])
    gone_id = await create(world, "gone")
    await service.change_status(done_id, world.dev_actor, S.REVIEW)
    await service.change_status(done_id, world.reviewer_actor, S.DONE)
    await service.soft_delete(gone_id, world.dev_actor)

    default = await service.list_tasks(TaskFilter(workspace_id=world.workspace.id))
    assert [t.id for t in default.items] == [open_id]
    everything = await service.list_tasks(
        TaskFilter(workspace_id=world.workspace.id, include_closed=True)
    )
    assert {t.id for t in everything.items} == {open_id, done_id}
    only_done = await service.list_tasks(
        TaskFilter(workspace_id=world.workspace.id, statuses=frozenset({S.DONE}))
    )
    assert [t.id for t in only_done.items] == [done_id]


async def test_list_filters_by_area_priority_and_assignee(world: World) -> None:
    service = TaskService(world.session)
    workspaces = WorkspaceService(world.session)
    mobile = await workspaces.add_area(world.workspace.id, "mobile", None)
    await workspaces.add_area(world.workspace.id, "backend", None)
    a = await create(
        world, "a", area_slug="mobile", priority=Priority.HIGH, assignee_usernames=["devalisher"]
    )
    await create(world, "b", area_slug="backend")
    await create(world, "c", area_slug="mobile", assignee_usernames=["devvalijon"])

    base = TaskFilter(workspace_id=world.workspace.id)
    by_area = await service.list_tasks(
        TaskFilter(workspace_id=base.workspace_id, area_id=mobile.id)
    )
    assert {t.title for t in by_area.items} == {"a", "c"}
    by_priority = await service.list_tasks(
        TaskFilter(workspace_id=base.workspace_id, priority=Priority.HIGH)
    )
    assert [t.id for t in by_priority.items] == [a]
    mine = await service.list_tasks(
        TaskFilter(workspace_id=base.workspace_id, assignee_id=world.dev2.id)
    )
    assert [t.title for t in mine.items] == ["c"]


async def test_list_pagination(world: World) -> None:
    service = TaskService(world.session)
    for i in range(7):
        await create(world, f"task {i}")
    flt = TaskFilter(workspace_id=world.workspace.id)
    first = await service.list_tasks(flt, page=0, page_size=3)
    last = await service.list_tasks(flt, page=2, page_size=3)
    beyond = await service.list_tasks(flt, page=99, page_size=3)
    assert (first.total, first.pages, len(first.items)) == (7, 3, 3)
    assert [t.number for t in last.items] == [7]
    assert beyond.page == 2  # clamped, never an empty page past the end


async def test_workspaces_are_isolated(world: World) -> None:
    other = await WorkspaceService(world.session).create(-1009, "Other", "uz", "Asia/Tashkent")
    await create(world, "mine")
    page = await TaskService(world.session).list_tasks(TaskFilter(workspace_id=other.id))
    assert page.total == 0
    with pytest.raises(NotFoundError):
        await TaskService(world.session).get(other.id, 1)


# ---- digest ---------------------------------------------------------------------------


async def test_digest_sections(world: World) -> None:
    service = TaskService(world.session)
    today = date(2026, 10, 10)
    overdue = await create(
        world, "overdue", due=today - timedelta(days=1), assignee_usernames=["devalisher"]
    )
    due_today = await create(world, "today", due=today, assignee_usernames=["devalisher"])
    reviewing = await create(world, "reviewing", assignee_usernames=["devalisher"])
    blocked = await create(world, "blocked", assignee_usernames=["devalisher"])
    nobody = await create(world, "nobody")
    await service.change_status(reviewing, world.dev_actor, S.REVIEW)
    await service.change_status(blocked, world.dev_actor, S.BLOCKED)

    digest = await service.digest(world.workspace.id, today)
    assert [t.id for t in digest.overdue] == [overdue]
    assert [t.id for t in digest.due_today] == [due_today]
    assert [t.id for t in digest.in_review] == [reviewing]
    assert [t.id for t in digest.blocked] == [blocked]
    assert [t.id for t in digest.unassigned] == [nobody]
    assert not digest.is_empty


async def test_digest_ignores_finished_work(world: World) -> None:
    service = TaskService(world.session)
    today = date(2026, 10, 10)
    task_id = await create(
        world, "old", due=today - timedelta(days=3), assignee_usernames=["devalisher"]
    )
    await service.change_status(task_id, world.dev_actor, S.REVIEW)
    await service.change_status(task_id, world.reviewer_actor, S.DONE)
    assert (await service.digest(world.workspace.id, today)).is_empty


# ---- workspace service ----------------------------------------------------------------


async def test_areas(world: World) -> None:
    workspaces = WorkspaceService(world.session)
    await workspaces.add_area(world.workspace.id, "#Mobile", "Mobil ilova")
    with pytest.raises(InputError) as dup:
        await workspaces.add_area(world.workspace.id, "mobile", None)
    assert dup.value.code == "area_exists"
    for bad in ("x", "1abc", "has space", "task", "t42"):
        with pytest.raises(InputError):
            await workspaces.add_area(world.workspace.id, bad, None)

    await create(world, "x", area_slug="mobile")
    listed = await workspaces.list_areas(world.workspace.id)
    assert [(a.slug, count) for a, count in listed] == [("mobile", 1)]

    await workspaces.remove_area(world.workspace.id, "mobile")
    task = (
        await TaskService(world.session).list_tasks(TaskFilter(workspace_id=world.workspace.id))
    ).items[0]
    await world.session.refresh(task, ["area"])
    assert task.area is None  # tasks survive their area
    with pytest.raises(NotFoundError):
        await workspaces.remove_area(world.workspace.id, "mobile")


async def test_roles_and_reviewers(world: World) -> None:
    workspaces = WorkspaceService(world.session)
    assert [u.id for u in await workspaces.reviewers(world.workspace.id)] == [world.reviewer.id]

    await workspaces.set_role(world.workspace.id, world.reviewer, Role.MEMBER)
    # with no reviewer left, admins review
    assert [u.id for u in await workspaces.reviewers(world.workspace.id)] == [world.admin.id]

    with pytest.raises(PermissionDenied) as last:
        await workspaces.set_role(world.workspace.id, world.admin, Role.MEMBER)
    assert last.value.code == "last_admin"

    members = await workspaces.list_members(world.workspace.id)
    assert members[0].role is Role.ADMIN


async def test_find_member_by_username_is_case_insensitive(world: World) -> None:
    workspaces = WorkspaceService(world.session)
    found = await workspaces.find_member_by_username(world.workspace.id, "@DevAlisher")
    assert found is not None
    assert found.id == world.dev.id
    assert await workspaces.find_member_by_username(world.workspace.id, "nobody") is None


async def test_require_membership(world: World) -> None:
    workspaces = WorkspaceService(world.session)
    with pytest.raises(AppError) as exc:
        await workspaces.require_membership(world.workspace.id, 424242)
    assert exc.value.code == "not_member"


async def test_chat_migration_keeps_workspace(world: World) -> None:
    workspaces = WorkspaceService(world.session)
    await workspaces.migrate_chat(world.workspace.telegram_chat_id or 0, -1009999999999)
    moved = await workspaces.find_by_chat(-1009999999999)
    assert moved is not None
    assert moved.id == world.workspace.id


# ---- search & history -----------------------------------------------------------------


async def test_search_finds_titles_and_descriptions_in_any_status(world: World) -> None:
    service = TaskService(world.session)
    login = await create(world, "Fix Login crash", description="happens on iOS")
    await create(world, "Update docs")
    done = await create(world, "Old LOGIN bug", assignee_usernames=["devalisher"])
    await service.change_status(done, world.dev_actor, S.REVIEW)
    await service.change_status(done, world.reviewer_actor, S.DONE)

    by_title = await service.search(world.workspace.id, "login")
    assert {t.title for t in by_title.items} == {"Fix Login crash", "Old LOGIN bug"}
    by_description = await service.search(world.workspace.id, "IOS")
    assert [t.id for t in by_description.items] == [login]
    assert (await service.search(world.workspace.id, "nothing like this")).total == 0


async def test_search_treats_wildcards_literally_and_limits_results(world: World) -> None:
    service = TaskService(world.session)
    await create(world, "100% done")
    await create(world, "plain title")
    assert [t.title for t in (await service.search(world.workspace.id, "100%")).items] == [
        "100% done"
    ]
    assert (await service.search(world.workspace.id, "%%")).total == 0

    for i in range(20):
        await create(world, f"bulk item {i}")
    page = await service.search(world.workspace.id, "bulk item", limit=15)
    assert (page.total, len(page.items)) == (20, 15)


async def test_search_needs_a_real_query_and_stays_in_the_workspace(world: World) -> None:
    service = TaskService(world.session)
    with pytest.raises(InputError) as exc:
        await service.search(world.workspace.id, " a ")
    assert exc.value.code == "find_usage"
    other = await WorkspaceService(world.session).create(-1009, "Other", "uz", "Asia/Tashkent")
    await create(world, "secret login")
    assert (await service.search(other.id, "login")).total == 0


async def test_history_lists_events_with_names(world: World) -> None:
    service = TaskService(world.session)
    task_id = await create(world, "Tracked")
    await service.assign(task_id, world.dev_actor, [world.dev2])
    await service.change_status(task_id, world.dev2_actor, S.BLOCKED, reason="waiting")
    await service.edit(task_id, world.dev_actor, TaskPatch(title="Tracked well"))

    history = await service.history(task_id)
    kinds = [h.event.type for h in history]
    assert kinds == [
        EventType.CREATED,
        EventType.ASSIGNED,
        EventType.STATUS_CHANGED,
        EventType.EDITED,
    ]
    assert history[0].actor_name == "Alisher"
    assigned = history[1]
    assert assigned.subject_name == "Valijon"
    assert history[2].event.data["reason"] == "waiting"


async def test_history_is_limited_to_the_latest_events(world: World) -> None:
    service = TaskService(world.session)
    task_id = await create(world, "Chatty")
    for i in range(10):
        await service.comment(task_id, world.dev_actor, f"note {i}")
    history = await service.history(task_id, limit=4)
    assert len(history) == 4
    assert history[0].event.id < history[-1].event.id  # oldest of the latest first
