from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.db.models import Area, Membership, Task, User, Workspace
from qul_bot.domain.areas import normalize_slug
from qul_bot.domain.enums import ACTIVE_STATUSES, Role
from qul_bot.domain.specialty import Specialty
from qul_bot.errors import InputError, NotFoundError, PermissionDenied


class WorkspaceService:
    """Workspaces, who belongs to them with which role, and their areas."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- workspaces -------------------------------------------------------------------

    async def find_by_chat(self, chat_id: int) -> Workspace | None:
        result = await self.session.execute(
            select(Workspace).where(Workspace.telegram_chat_id == chat_id)
        )
        return result.scalar_one_or_none()

    async def create(self, chat_id: int, title: str, locale: str, timezone: str) -> Workspace:
        try:
            async with self.session.begin_nested():
                workspace = Workspace(
                    telegram_chat_id=chat_id, title=title, locale=locale, timezone=timezone
                )
                self.session.add(workspace)
        except IntegrityError:
            existing = await self.find_by_chat(chat_id)
            assert existing is not None
            return existing
        return workspace

    async def next_task_number(self, workspace_id: int) -> int:
        """Atomically reserve the next task number (row-locked until the transaction ends)."""
        result = await self.session.execute(
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(task_counter=Workspace.task_counter + 1)
            .returning(Workspace.task_counter)
            .execution_options(synchronize_session=False)
        )
        return int(result.scalar_one())

    async def migrate_chat(self, old_chat_id: int, new_chat_id: int) -> None:
        """A basic group was upgraded to a supergroup: Telegram gives it a new chat id."""
        await self.session.execute(
            update(Workspace)
            .where(Workspace.telegram_chat_id == old_chat_id)
            .values(telegram_chat_id=new_chat_id)
        )

    # ---- membership -------------------------------------------------------------------

    async def get_membership(self, workspace_id: int, user_id: int) -> Membership | None:
        return await self.session.get(Membership, (workspace_id, user_id))

    async def require_membership(self, workspace_id: int, user_id: int) -> Membership:
        membership = await self.get_membership(workspace_id, user_id)
        if membership is None:
            raise PermissionDenied("not_member")
        return membership

    async def add_member(self, workspace_id: int, user: User, role: Role) -> Membership:
        try:
            async with self.session.begin_nested():
                membership = Membership(workspace_id=workspace_id, user_id=user.id, role=role)
                self.session.add(membership)
        except IntegrityError:
            membership = await self.require_membership(workspace_id, user.id)
        membership.user = user
        return membership

    async def sole_workspace_of(self, user_id: int) -> tuple[Workspace, Membership] | None:
        """For private chats: the user's workspace, if they belong to exactly one."""
        result = await self.session.execute(
            select(Membership).where(Membership.user_id == user_id).limit(2)
        )
        memberships = result.scalars().all()
        if len(memberships) != 1:
            return None
        workspace = await self.session.get(Workspace, memberships[0].workspace_id)
        assert workspace is not None
        return workspace, memberships[0]

    async def list_members(self, workspace_id: int) -> list[Membership]:
        result = await self.session.execute(
            select(Membership).where(Membership.workspace_id == workspace_id)
        )
        members = list(result.scalars().all())
        order = {Role.ADMIN: 0, Role.REVIEWER: 1, Role.MEMBER: 2}
        members.sort(key=lambda m: (order[m.role], m.user.display_name.lower()))
        return members

    async def find_member_by_username(self, workspace_id: int, username: str) -> User | None:
        result = await self.session.execute(
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(
                Membership.workspace_id == workspace_id,
                func.lower(User.username) == username.lower().lstrip("@"),
            )
        )
        return result.scalar_one_or_none()

    async def set_role(self, workspace_id: int, user: User, role: Role) -> Membership:
        membership = await self.require_membership(workspace_id, user.id)
        if membership.role is Role.ADMIN and role is not Role.ADMIN:
            admins = await self.session.scalar(
                select(func.count())
                .select_from(Membership)
                .where(Membership.workspace_id == workspace_id, Membership.role == Role.ADMIN)
            )
            if (admins or 0) <= 1:
                raise PermissionDenied("last_admin")
        membership.role = role
        return membership

    async def set_specialty(
        self,
        workspace_id: int,
        target: User,
        specialty: Specialty | None,
        actor_id: int,
        actor_role: Role,
    ) -> Membership:
        """People set their own specialty; admins can set anyone's."""
        if actor_id != target.id and actor_role is not Role.ADMIN:
            raise PermissionDenied("admin_required")
        membership = await self.require_membership(workspace_id, target.id)
        membership.specialty = specialty
        return membership

    async def reviewers(self, workspace_id: int) -> list[User]:
        """Who should be asked to review: reviewers, or admins if there are none."""
        members = await self.list_members(workspace_id)
        reviewers = [m.user for m in members if m.role is Role.REVIEWER]
        return reviewers or [m.user for m in members if m.role is Role.ADMIN]

    # ---- areas ------------------------------------------------------------------------

    async def get_area(self, workspace_id: int, slug: str) -> Area | None:
        result = await self.session.execute(
            select(Area).where(Area.workspace_id == workspace_id, Area.slug == slug.lower())
        )
        return result.scalar_one_or_none()

    async def list_areas(self, workspace_id: int) -> list[tuple[Area, int]]:
        """Areas with their number of active tasks."""
        counts = (
            select(Task.area_id, func.count().label("n"))
            .where(
                Task.workspace_id == workspace_id,
                Task.deleted_at.is_(None),
                Task.status.in_(ACTIVE_STATUSES),
            )
            .group_by(Task.area_id)
            .subquery()
        )
        result = await self.session.execute(
            select(Area, func.coalesce(counts.c.n, 0))
            .outerjoin(counts, counts.c.area_id == Area.id)
            .where(Area.workspace_id == workspace_id)
            .order_by(Area.slug)
        )
        return [(area, int(n)) for area, n in result.all()]

    async def add_area(self, workspace_id: int, raw_slug: str, name: str | None) -> Area:
        slug = normalize_slug(raw_slug)
        name = (name or "").strip() or slug
        if len(name) > 64:
            raise InputError("area_name_too_long", max=64)
        if await self.get_area(workspace_id, slug):
            raise InputError("area_exists", slug=slug)
        area = Area(workspace_id=workspace_id, slug=slug, name=name)
        self.session.add(area)
        await self.session.flush()
        return area

    async def remove_area(self, workspace_id: int, raw_slug: str) -> Area:
        area = await self.get_area(workspace_id, raw_slug.strip().lstrip("#"))
        if area is None:
            raise NotFoundError("unknown_area", slug=raw_slug)
        await self.session.delete(area)
        await self.session.flush()
        return area
