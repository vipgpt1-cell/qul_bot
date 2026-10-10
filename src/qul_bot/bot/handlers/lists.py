"""Task lists: /list, /my, /review, /digest and the /<area> shortcuts."""

from __future__ import annotations

import re

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.bot.context import RequestContext
from qul_bot.bot.formatting import (
    esc,
    priority_label,
    render_digest,
    render_task_list,
    status_label,
)
from qul_bot.bot.keyboards import pagination_keyboard
from qul_bot.db.models import User
from qul_bot.domain.enums import TaskStatus
from qul_bot.errors import InputError, NotFoundError
from qul_bot.i18n import Translator
from qul_bot.parsing.task_input import ListInput, parse_list_input
from qul_bot.services.tasks import DIGEST_SECTION_LIMIT, TaskFilter, TaskService
from qul_bot.services.workspaces import WorkspaceService

PAGE_SIZE = 15


async def build_filter(
    session: AsyncSession,
    ctx: RequestContext,
    parsed: ListInput,
    *,
    assignee: User | None = None,
    statuses: frozenset[TaskStatus] = frozenset(),
) -> TaskFilter:
    workspace = ctx.require_workspace()
    workspaces = WorkspaceService(session)

    area_id: int | None = None
    if parsed.area:
        area = await workspaces.get_area(workspace.id, parsed.area)
        if area is None:
            raise NotFoundError("unknown_area", slug=parsed.area)
        area_id = area.id

    if assignee is None and parsed.assignees:
        if len(parsed.assignees) > 1:
            raise InputError("bad_filter", word=f"@{parsed.assignees[1]}")
        found = await workspaces.find_member_by_username(workspace.id, parsed.assignees[0])
        if found is None:
            raise NotFoundError("unknown_user", username=parsed.assignees[0])
        assignee = found

    return TaskFilter(
        workspace_id=workspace.id,
        area_id=area_id,
        statuses=statuses | frozenset(parsed.statuses),
        priority=parsed.priority,
        assignee_id=assignee.id if assignee else None,
        include_closed=parsed.include_closed,
    )


async def list_title(session: AsyncSession, t: Translator, flt: TaskFilter) -> str:
    """Describe the active filter, e.g. `📋 Vazifalar · 👤 Ali · #mobile · 🟠 Yuqori`."""
    parts = [t("list.title")]
    if flt.assignee_id:
        user = await session.get(User, flt.assignee_id)
        if user:
            parts.append(f"👤 {esc(user.display_name)}")
    if flt.area_id:
        workspaces = WorkspaceService(session)
        for area, _ in await workspaces.list_areas(flt.workspace_id):
            if area.id == flt.area_id:
                parts.append(f"#{esc(area.slug)}")
    if flt.priority:
        parts.append(priority_label(t, flt.priority))
    parts += [status_label(t, status) for status in flt.statuses]
    if flt.include_closed and not flt.statuses:
        parts.append(t("list.with_closed"))
    return " · ".join(parts)


async def send_list(
    message: Message, session: AsyncSession, ctx: RequestContext, flt: TaskFilter
) -> None:
    page = await TaskService(session).list_tasks(flt, 0, PAGE_SIZE)
    title = await list_title(session, ctx.t, flt)
    await message.answer(
        render_task_list(ctx.t, page, title, ctx.today),
        reply_markup=pagination_keyboard(flt, page.page, page.pages),
    )


async def cmd_list(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    flt = await build_filter(session, ctx, parse_list_input(command.args or ""))
    await send_list(message, session, ctx, flt)


async def cmd_my(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    flt = await build_filter(session, ctx, parse_list_input(command.args or ""), assignee=ctx.user)
    await send_list(message, session, ctx, flt)


async def cmd_review(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    flt = await build_filter(
        session,
        ctx,
        parse_list_input(command.args or ""),
        statuses=frozenset({TaskStatus.REVIEW}),
    )
    await send_list(message, session, ctx, flt)


async def cmd_digest(message: Message, session: AsyncSession, ctx: RequestContext) -> None:
    workspace = ctx.require_workspace()
    digest = await TaskService(session).digest(workspace.id, ctx.today)
    await message.answer(render_digest(ctx.t, digest, ctx.today, DIGEST_SECTION_LIMIT))


async def cmd_area_shortcut(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    workspace = ctx.workspace
    if workspace is None:
        return
    slug = (command.command or "").lower()
    if await WorkspaceService(session).get_area(workspace.id, slug) is None:
        return  # some other bot's command, or a typo: stay quiet
    flt = await build_filter(
        session, ctx, ListInput(area=slug) if not command.args else _with_area(command.args, slug)
    )
    await send_list(message, session, ctx, flt)


def _with_area(args: str, slug: str) -> ListInput:
    parsed = parse_list_input(args)
    parsed.area = slug
    return parsed


def register(router: Router) -> None:
    router.message.register(cmd_list, Command("list", ignore_case=True))
    router.message.register(cmd_my, Command("my", ignore_case=True))
    router.message.register(cmd_review, Command("review", ignore_case=True))
    router.message.register(cmd_digest, Command("digest", ignore_case=True))


def register_shortcuts(router: Router) -> None:
    router.message.register(cmd_area_shortcut, Command(re.compile(r"[A-Za-z][A-Za-z0-9_]*$")))
