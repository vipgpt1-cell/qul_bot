"""Creating, viewing and changing single tasks."""

from __future__ import annotations

import re

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.bot.commands import (
    DONE_COMMAND,
    REASON_COMMANDS,
    STATUS_COMMANDS,
    TASK_COMMANDS,
)
from qul_bot.bot.context import RequestContext
from qul_bot.bot.formatting import (
    esc,
    mentions,
    render_card,
    render_history,
    render_status_change,
    truncate,
    user_name,
)
from qul_bot.bot.handlers.helpers import (
    replied_user,
    reply_to,
    resolve_ref,
    resolve_usernames,
)
from qul_bot.bot.keyboards import confirm_delete_keyboard, task_keyboard
from qul_bot.db.models import Task
from qul_bot.domain.enums import Priority
from qul_bot.domain.workflow import TaskState, can_delete, done_target
from qul_bot.errors import InputError, PermissionDenied
from qul_bot.parsing.task_input import MAX_TITLE_LENGTH, TaskInput, parse_task_input
from qul_bot.services.tasks import NewTask, TaskPatch, TaskService

_TASK_SHORTCUT = re.compile(r"t(\d+)$", re.IGNORECASE)


def patch_from_input(parsed: TaskInput) -> TaskPatch:
    return TaskPatch(
        title=parsed.title or None,
        description=parsed.description or None,
        priority=parsed.priority,
        area_slug=parsed.area,
        clear_area=parsed.clear_area,
        due=parsed.due,
        clear_due=parsed.clear_due,
    )


async def answer_card(
    message: Message,
    ctx: RequestContext,
    session: AsyncSession,
    task: Task,
    *,
    header: str | None = None,
    footer: str | None = None,
    reply_to_message_id: int | None = None,
) -> None:
    comments = await TaskService(session).recent_comments(task.id)
    text = render_card(ctx.t, task, ctx.today, comments, header)
    if footer:
        text += f"\n\n{footer}"
    await message.answer(
        text,
        reply_markup=task_keyboard(ctx.t, task),
        reply_parameters=reply_to(reply_to_message_id),
    )


# ---- create ---------------------------------------------------------------------------


async def cmd_task(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    workspace = ctx.require_workspace()
    parsed = parse_task_input(command.args or "", ctx.today)
    title, description = parsed.title, parsed.description
    source = message.reply_to_message
    if source is not None and source.from_user is not None and source.from_user.is_bot:
        source = None  # replying to a bot card is not "make this message a task"
    source_message_id: int | None = None

    if source is not None:
        quoted = (source.text or source.caption or "").strip()
        if not title and quoted:
            first_line = quoted.split("\n", 1)[0]
            title = truncate(first_line, MAX_TITLE_LENGTH)
            if title != quoted:  # more than the title was said: keep it all as context
                description = quoted
        elif quoted and not description:
            description = quoted
        source_message_id = source.message_id

    if not title:
        raise InputError("empty_title")

    service = TaskService(session)
    task = await service.create(
        workspace,
        ctx.user,
        NewTask(
            title=title,
            description=description,
            area_slug=parsed.area,
            priority=parsed.priority or Priority.NORMAL,
            assignee_usernames=parsed.assignees,
            due=parsed.due,
            source_chat_id=message.chat.id if source_message_id else None,
            source_message_id=source_message_id,
        ),
    )
    others = [u for u in task.assignees if u.id != ctx.user.id]
    footer = ctx.t("notify.assigned", users=mentions(others)) if others else None
    await answer_card(
        message,
        ctx,
        session,
        task,
        header=ctx.t("created.header"),
        footer=footer,
        reply_to_message_id=source_message_id,
    )


# ---- view -----------------------------------------------------------------------------


async def _show(message: Message, ctx: RequestContext, session: AsyncSession, number: int) -> None:
    workspace = ctx.require_workspace()
    task = await TaskService(session).get(workspace.id, number)
    await answer_card(message, ctx, session, task)


async def cmd_info(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    number, _ = resolve_ref(message, command.args)
    await _show(message, ctx, session, number)


async def cmd_history(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    workspace = ctx.require_workspace()
    number, _ = resolve_ref(message, command.args)
    service = TaskService(session)
    task = await service.get(workspace.id, number)
    entries = await service.history(task.id)
    await message.answer(render_history(ctx.t, task, entries, ctx.tz))


async def cmd_task_shortcut(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    """`/t42` — the tappable form of a task number used in lists."""
    assert command.regexp_match is not None
    await _show(message, ctx, session, int(command.regexp_match.group(1)))


# ---- change ---------------------------------------------------------------------------


async def cmd_edit(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    workspace = ctx.require_workspace()
    number, rest = resolve_ref(message, command.args)
    parsed = parse_task_input(rest, ctx.today)
    patch = patch_from_input(parsed)
    if patch.is_empty() and not parsed.assignees:
        raise InputError("nothing_to_edit")

    service = TaskService(session)
    task = await service.get(workspace.id, number)
    users = await resolve_usernames(session, ctx, parsed.assignees)
    changes = await service.edit(task.id, ctx.actor, patch)
    added = await service.assign(task.id, ctx.actor, users) if users else []
    if not changes and not added:
        raise InputError("nothing_changed")

    task = await service.get(workspace.id, number)
    footer = ctx.t("notify.assigned", users=mentions(added)) if added else None
    await answer_card(
        message, ctx, session, task, header=ctx.t("edited.header", number=number), footer=footer
    )


async def cmd_assign(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    """`/assign 42 @user`, or reply to a person's message, or just `/assign 42` for yourself."""
    workspace = ctx.require_workspace()
    number, rest = resolve_ref(message, command.args)
    users = await resolve_usernames(session, ctx, parse_task_input(rest, ctx.today).assignees)
    if replied := await replied_user(session, ctx, message):
        users.append(replied)
    if not users:
        users = [ctx.user]

    service = TaskService(session)
    task = await service.get(workspace.id, number)
    if (command.command or "").lower() == "unassign":
        removed = await service.unassign(task.id, ctx.actor, users)
        if not removed:
            raise InputError("not_assigned", number=number)
        text = ctx.t(
            "unassigned.done", number=number, users=esc(", ".join(u.display_name for u in removed))
        )
    else:
        added = await service.assign(task.id, ctx.actor, users)
        if not added:
            raise InputError("already_assigned", number=number)
        text = ctx.t("assigned.done", number=number, users=mentions(added))
    await message.answer(text)


async def cmd_comment(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    workspace = ctx.require_workspace()
    number, body = resolve_ref(message, command.args)
    service = TaskService(session)
    task = await service.get(workspace.id, number)
    await service.comment(task.id, ctx.actor, body)
    await message.answer(
        ctx.t(
            "comment.done", number=number, user=user_name(ctx.user), text=esc(truncate(body, 300))
        )
    )


async def cmd_status(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    workspace = ctx.require_workspace()
    name = (command.command or "").lower()
    number, rest = resolve_ref(message, command.args)
    service = TaskService(session)
    task = await service.get(workspace.id, number)

    target = done_target(task.status) if name == DONE_COMMAND else STATUS_COMMANDS[name]
    reason = rest if name in REASON_COMMANDS else None
    change = await service.change_status(task.id, ctx.actor, target, reason)

    reviewers = await service.workspaces.reviewers(workspace.id)
    await message.answer(
        render_status_change(ctx.t, change, ctx.user, reason=reason, reviewers=reviewers)
    )


# ---- delete / restore -----------------------------------------------------------------


async def cmd_delete(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    workspace = ctx.require_workspace()
    number, _ = resolve_ref(message, command.args)
    task = await TaskService(session).get(workspace.id, number)
    state = TaskState(task.status, task.reporter_id, [u.id for u in task.assignees])
    if not can_delete(state, ctx.actor):
        raise PermissionDenied("delete_denied")
    await message.answer(
        ctx.t("delete.confirm", number=number, title=esc(truncate(task.title, 100))),
        reply_markup=confirm_delete_keyboard(ctx.t, task),
    )


async def cmd_restore(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    workspace = ctx.require_workspace()
    number, _ = resolve_ref(message, command.args)
    task = await TaskService(session).restore(workspace.id, number, ctx.actor)
    await answer_card(message, ctx, session, task, header=ctx.t("restored.header", number=number))


def register(router: Router) -> None:
    router.message.register(cmd_task, Command(*TASK_COMMANDS, ignore_case=True))
    router.message.register(cmd_info, Command("info", ignore_case=True))
    router.message.register(cmd_history, Command("history", ignore_case=True))
    router.message.register(cmd_task_shortcut, Command(_TASK_SHORTCUT))
    router.message.register(cmd_edit, Command("edit", ignore_case=True))
    router.message.register(cmd_assign, Command("assign", "unassign", ignore_case=True))
    router.message.register(cmd_comment, Command("comment", ignore_case=True))
    router.message.register(cmd_status, Command(*STATUS_COMMANDS, DONE_COMMAND, ignore_case=True))
    router.message.register(cmd_delete, Command("delete", ignore_case=True))
    router.message.register(cmd_restore, Command("restore", ignore_case=True))
