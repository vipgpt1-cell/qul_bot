from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.db.models import Task, TaskComment, TaskEvent, User, Workspace, task_assignees
from qul_bot.db.types import utcnow
from qul_bot.domain.enums import (
    ACTIVE_STATUSES,
    PRIORITY_ORDER,
    STATUS_ORDER,
    EventType,
    Priority,
    Role,
    TaskStatus,
)
from qul_bot.domain.workflow import (
    AUTO_ASSIGN_TARGETS,
    Actor,
    TaskState,
    can_delete,
    can_modify,
    check_transition,
)
from qul_bot.errors import InputError, NotFoundError, PermissionDenied
from qul_bot.services.workspaces import WorkspaceService

MAX_COMMENT_LENGTH = 2000
DIGEST_SECTION_LIMIT = 10


@dataclass(slots=True)
class NewTask:
    title: str
    description: str | None = None
    area_slug: str | None = None
    priority: Priority = Priority.NORMAL
    assignee_usernames: list[str] = field(default_factory=list)
    due: date | None = None
    source_chat_id: int | None = None
    source_message_id: int | None = None


@dataclass(slots=True)
class TaskPatch:
    """Fields to change; `None` means "leave as is" unless the matching `clear_*` flag is set."""

    title: str | None = None
    description: str | None = None
    priority: Priority | None = None
    area_slug: str | None = None
    clear_area: bool = False
    due: date | None = None
    clear_due: bool = False

    def is_empty(self) -> bool:
        return (
            self.title is None
            and self.description is None
            and self.priority is None
            and self.area_slug is None
            and not self.clear_area
            and self.due is None
            and not self.clear_due
        )


@dataclass(frozen=True, slots=True)
class StatusChange:
    task: Task
    previous: TaskStatus
    auto_assigned: bool


@dataclass(frozen=True, slots=True)
class TaskFilter:
    """Which tasks a list shows. Also round-trips through inline-button callback data."""

    workspace_id: int
    area_id: int | None = None
    statuses: frozenset[TaskStatus] = frozenset()
    priority: Priority | None = None
    assignee_id: int | None = None
    include_closed: bool = False

    def effective_statuses(self) -> tuple[TaskStatus, ...]:
        if self.statuses:
            return tuple(s for s in STATUS_ORDER if s in self.statuses)
        if self.include_closed:
            return STATUS_ORDER
        return ACTIVE_STATUSES


@dataclass(frozen=True, slots=True)
class TaskPage:
    items: Sequence[Task]
    total: int
    page: int
    pages: int


@dataclass(frozen=True, slots=True)
class Digest:
    overdue: list[Task]
    due_today: list[Task]
    in_review: list[Task]
    blocked: list[Task]
    unassigned: list[Task]

    @property
    def is_empty(self) -> bool:
        return not (
            self.overdue or self.due_today or self.in_review or self.blocked or self.unassigned
        )


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    event: TaskEvent
    actor_name: str
    #: Display name of the person an assign/unassign event is about, if any.
    subject_name: str | None


def _state(task: Task) -> TaskState:
    return TaskState(
        status=task.status,
        reporter_id=task.reporter_id,
        assignee_ids=frozenset(u.id for u in task.assignees),
    )


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.workspaces = WorkspaceService(session)

    # ---- reading ----------------------------------------------------------------------

    async def get_by_id(
        self, task_id: int, *, for_update: bool = False, include_deleted: bool = False
    ) -> Task:
        stmt = select(Task).where(Task.id == task_id)
        if not include_deleted:
            stmt = stmt.where(Task.deleted_at.is_(None))
        if for_update:
            # `of=Task` keeps eager-loaded relationships out of the row lock.
            stmt = stmt.with_for_update(of=Task)
        task = (await self.session.execute(stmt)).scalar_one_or_none()
        if task is None:
            raise NotFoundError("task_gone")
        return task

    async def get(
        self,
        workspace_id: int,
        number: int,
        *,
        for_update: bool = False,
        include_deleted: bool = False,
    ) -> Task:
        stmt = select(Task).where(Task.workspace_id == workspace_id, Task.number == number)
        if not include_deleted:
            stmt = stmt.where(Task.deleted_at.is_(None))
        if for_update:
            stmt = stmt.with_for_update(of=Task)
        task = (await self.session.execute(stmt)).scalar_one_or_none()
        if task is None:
            raise NotFoundError("task_not_found", number=number)
        return task

    async def recent_comments(self, task_id: int, limit: int = 5) -> list[TaskComment]:
        result = await self.session.execute(
            select(TaskComment)
            .where(TaskComment.task_id == task_id)
            .order_by(TaskComment.id.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def list_tasks(self, flt: TaskFilter, page: int = 0, page_size: int = 15) -> TaskPage:
        stmt = select(Task).where(
            Task.workspace_id == flt.workspace_id,
            Task.deleted_at.is_(None),
            Task.status.in_(flt.effective_statuses()),
        )
        if flt.area_id is not None:
            stmt = stmt.where(Task.area_id == flt.area_id)
        if flt.priority is not None:
            stmt = stmt.where(Task.priority == flt.priority)
        if flt.assignee_id is not None:
            stmt = stmt.where(
                Task.id.in_(
                    select(task_assignees.c.task_id).where(
                        task_assignees.c.user_id == flt.assignee_id
                    )
                )
            )

        total = (await self.session.scalar(select(func.count()).select_from(stmt.subquery()))) or 0
        pages = max(1, math.ceil(total / page_size))
        page = min(max(page, 0), pages - 1)

        status_rank = case({s: i for i, s in enumerate(STATUS_ORDER)}, value=Task.status)
        priority_rank = case({p: i for i, p in enumerate(PRIORITY_ORDER)}, value=Task.priority)
        far_future = date(9999, 12, 31)
        stmt = (
            stmt.order_by(
                status_rank,
                priority_rank,
                func.coalesce(Task.due_date, far_future),
                Task.number,
            )
            .limit(page_size)
            .offset(page * page_size)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return TaskPage(items=items, total=total, page=page, pages=pages)

    async def search(self, workspace_id: int, query: str, limit: int = 15) -> TaskPage:
        """Tasks whose title or description contains `query` (any status, case-insensitive)."""
        needle = query.strip().lower()
        if len(needle) < 2:
            raise InputError("find_usage")
        match = or_(
            func.lower(Task.title).contains(needle, autoescape=True),
            func.lower(func.coalesce(Task.description, "")).contains(needle, autoescape=True),
        )
        base = select(Task).where(
            Task.workspace_id == workspace_id, Task.deleted_at.is_(None), match
        )
        total = (await self.session.scalar(select(func.count()).select_from(base.subquery()))) or 0
        status_rank = case({s: i for i, s in enumerate(STATUS_ORDER)}, value=Task.status)
        rows = (
            (
                await self.session.execute(
                    base.order_by(status_rank, Task.number.desc()).limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return TaskPage(items=rows, total=total, page=0, pages=1)

    async def history(self, task_id: int, limit: int = 15) -> list[HistoryEntry]:
        """The most recent events of a task, oldest first, with people's names resolved."""
        result = await self.session.execute(
            select(TaskEvent)
            .where(TaskEvent.task_id == task_id)
            .order_by(TaskEvent.id.desc())
            .limit(limit)
        )
        events = list(reversed(result.scalars().all()))
        subject_ids = {
            int(e.data["user_id"]) for e in events if isinstance(e.data.get("user_id"), int)
        }
        names: dict[int, str] = {}
        if subject_ids:
            users = await self.session.execute(select(User).where(User.id.in_(subject_ids)))
            names = {u.id: u.display_name for u in users.scalars().all()}
        return [
            HistoryEntry(
                event=e,
                actor_name=e.actor.display_name if e.actor else "—",
                subject_name=names.get(int(e.data["user_id"])) if "user_id" in e.data else None,
            )
            for e in events
        ]

    async def digest(self, workspace_id: int, today: date) -> Digest:
        result = await self.session.execute(
            select(Task)
            .where(
                Task.workspace_id == workspace_id,
                Task.deleted_at.is_(None),
                Task.status.in_(ACTIVE_STATUSES),
            )
            .order_by(Task.due_date, Task.number)
        )
        active = result.scalars().all()
        return Digest(
            overdue=[t for t in active if t.due_date and t.due_date < today],
            due_today=[t for t in active if t.due_date == today],
            in_review=[t for t in active if t.status is TaskStatus.REVIEW],
            blocked=[t for t in active if t.status is TaskStatus.BLOCKED],
            unassigned=[t for t in active if not t.assignees and t.status is not TaskStatus.REVIEW],
        )

    # ---- writing ----------------------------------------------------------------------

    async def create(
        self,
        workspace: Workspace,
        reporter: User,
        data: NewTask,
        extra_assignees: Sequence[User] = (),
    ) -> Task:
        title = data.title.strip()
        if not title:
            raise InputError("empty_title")

        area_id: int | None = None
        if data.area_slug:
            area = await self.workspaces.get_area(workspace.id, data.area_slug)
            if area is None:
                raise NotFoundError("unknown_area", slug=data.area_slug)
            area_id = area.id

        assignees = list(extra_assignees)
        for username in data.assignee_usernames:
            user = await self.workspaces.find_member_by_username(workspace.id, username)
            if user is None:
                raise NotFoundError("unknown_user", username=username)
            assignees.append(user)
        unique = list({u.id: u for u in assignees}.values())

        number = await self.workspaces.next_task_number(workspace.id)
        task = Task(
            workspace_id=workspace.id,
            number=number,
            title=title,
            description=(data.description or "").strip() or None,
            priority=data.priority,
            area_id=area_id,
            reporter_id=reporter.id,
            due_date=data.due,
            source_chat_id=data.source_chat_id,
            source_message_id=data.source_message_id,
            status=TaskStatus.TODO,
        )
        task.assignees = unique
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task, ["area", "reporter", "assignees"])
        self._log(
            task,
            reporter.id,
            EventType.CREATED,
            title=title,
            priority=task.priority.value,
            area=task.area.slug if task.area else None,
            assignees=[u.id for u in unique],
            due=task.due_date.isoformat() if task.due_date else None,
        )
        return task

    async def change_status(
        self,
        task_id: int,
        actor: Actor,
        target: TaskStatus,
        reason: str | None = None,
    ) -> StatusChange:
        task = await self.get_by_id(task_id, for_update=True)
        check_transition(_state(task), target, actor)

        previous = task.status
        task.status = target
        task.completed_at = utcnow() if target is TaskStatus.DONE else None

        auto_assigned = False
        if target in AUTO_ASSIGN_TARGETS and not task.assignees:
            user = await self.session.get(User, actor.user_id)
            assert user is not None
            task.assignees.append(user)
            auto_assigned = True
            self._log(task, actor.user_id, EventType.ASSIGNED, user_id=user.id, auto=True)

        reason = (reason or "").strip() or None
        if reason:
            self._add_comment(task, actor.user_id, reason)
        self._log(
            task,
            actor.user_id,
            EventType.STATUS_CHANGED,
            source=previous.value,
            target=target.value,
            reason=reason,
        )
        await self.session.flush()
        return StatusChange(task=task, previous=previous, auto_assigned=auto_assigned)

    async def assign(self, task_id: int, actor: Actor, users: Sequence[User]) -> list[User]:
        """Add assignees; returns the ones that were not assigned yet."""
        task = await self.get_by_id(task_id, for_update=True)
        self._require_modify(task, actor)
        current = {u.id for u in task.assignees}
        added = [u for u in dict.fromkeys(users) if u.id not in current]
        for user in added:
            task.assignees.append(user)
            self._log(task, actor.user_id, EventType.ASSIGNED, user_id=user.id)
        if added:
            task.updated_at = utcnow()
            await self.session.flush()
        return added

    async def unassign(self, task_id: int, actor: Actor, users: Sequence[User]) -> list[User]:
        task = await self.get_by_id(task_id, for_update=True)
        self._require_modify(task, actor)
        wanted = {u.id for u in users}
        removed = [u for u in task.assignees if u.id in wanted]
        for user in removed:
            task.assignees.remove(user)
            self._log(task, actor.user_id, EventType.UNASSIGNED, user_id=user.id)
        if removed:
            task.updated_at = utcnow()
            await self.session.flush()
        return removed

    async def edit(self, task_id: int, actor: Actor, patch: TaskPatch) -> dict[str, Any]:
        """Apply a patch; returns `{field: [old, new]}` for what actually changed."""
        task = await self.get_by_id(task_id, for_update=True)
        self._require_modify(task, actor)
        changes: dict[str, Any] = {}

        if patch.title is not None and patch.title != task.title:
            changes["title"] = [task.title, patch.title]
            task.title = patch.title
        if patch.description is not None and (patch.description or None) != task.description:
            changes["description"] = [task.description, patch.description or None]
            task.description = patch.description or None
        if patch.priority is not None and patch.priority is not task.priority:
            changes["priority"] = [task.priority.value, patch.priority.value]
            task.priority = patch.priority
        if patch.clear_area or patch.area_slug is not None:
            new_area = None
            if patch.area_slug is not None:
                new_area = await self.workspaces.get_area(task.workspace_id, patch.area_slug)
                if new_area is None:
                    raise NotFoundError("unknown_area", slug=patch.area_slug)
            if (new_area.id if new_area else None) != task.area_id:
                changes["area"] = [
                    task.area.slug if task.area else None,
                    new_area.slug if new_area else None,
                ]
                task.area_id = new_area.id if new_area else None
                task.area = new_area
        if patch.clear_due or patch.due is not None:
            new_due = None if patch.clear_due else patch.due
            if new_due != task.due_date:
                changes["due"] = [
                    task.due_date.isoformat() if task.due_date else None,
                    new_due.isoformat() if new_due else None,
                ]
                task.due_date = new_due

        if changes:
            task.updated_at = utcnow()
            self._log(task, actor.user_id, EventType.EDITED, changes=changes)
            await self.session.flush()
        return changes

    async def comment(self, task_id: int, actor: Actor, body: str) -> TaskComment:
        body = body.strip()
        if not body:
            raise InputError("empty_comment")
        if len(body) > MAX_COMMENT_LENGTH:
            raise InputError("comment_too_long", max=MAX_COMMENT_LENGTH)
        task = await self.get_by_id(task_id)
        comment = self._add_comment(task, actor.user_id, body)
        self._log(task, actor.user_id, EventType.COMMENTED)
        await self.session.flush()
        return comment

    async def soft_delete(self, task_id: int, actor: Actor) -> Task:
        task = await self.get_by_id(task_id, for_update=True)
        if not can_delete(_state(task), actor):
            raise PermissionDenied("delete_denied")
        task.deleted_at = utcnow()
        self._log(task, actor.user_id, EventType.DELETED)
        await self.session.flush()
        return task

    async def restore(self, workspace_id: int, number: int, actor: Actor) -> Task:
        if actor.role is not Role.ADMIN:
            raise PermissionDenied("admin_required")
        task = await self.get(workspace_id, number, for_update=True, include_deleted=True)
        if task.deleted_at is None:
            raise InputError("not_deleted", number=number)
        task.deleted_at = None
        self._log(task, actor.user_id, EventType.RESTORED)
        await self.session.flush()
        return task

    # ---- internals --------------------------------------------------------------------

    def _require_modify(self, task: Task, actor: Actor) -> None:
        if not can_modify(_state(task), actor):
            raise PermissionDenied("not_involved")

    def _add_comment(self, task: Task, author_id: int, body: str) -> TaskComment:
        comment = TaskComment(task_id=task.id, author_id=author_id, body=body)
        self.session.add(comment)
        return comment

    def _log(self, task: Task, actor_id: int | None, event: EventType, **data: Any) -> None:
        self.session.add(
            TaskEvent(
                task_id=task.id,
                workspace_id=task.workspace_id,
                actor_id=actor_id,
                type=event,
                data=data,
            )
        )
