"""Inline-button presses on task cards and list pages."""

from __future__ import annotations

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.bot.callbacks import (
    ACTION_ASSIGN,
    ACTION_DELETE_NO,
    ACTION_DELETE_YES,
    ACTION_ME,
    ACTION_PRIORITY,
    ACTION_TARGETS,
    AssignPick,
    ListPage,
    SpecialtyPick,
    TaskAction,
    decode_filter,
)
from qul_bot.bot.context import RequestContext
from qul_bot.bot.formatting import (
    mention,
    render_card,
    render_status_change,
    render_task_list,
    specialty_label,
)
from qul_bot.bot.handlers.lists import PAGE_SIZE, list_title
from qul_bot.bot.keyboards import (
    assign_group_keyboard,
    assign_menu_keyboard,
    pagination_keyboard,
    task_keyboard,
)
from qul_bot.db.models import Task, User
from qul_bot.domain.enums import Priority
from qul_bot.domain.specialty import from_code
from qul_bot.domain.workflow import Actor
from qul_bot.errors import AppError
from qul_bot.services.tasks import TaskPatch, TaskService
from qul_bot.services.workspaces import WorkspaceService

_NEXT_PRIORITY = {
    Priority.LOW: Priority.NORMAL,
    Priority.NORMAL: Priority.HIGH,
    Priority.HIGH: Priority.URGENT,
    Priority.URGENT: Priority.LOW,
}


async def _edit(message: Message, text: str, reply_markup: object = None) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)  # type: ignore[arg-type]
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise


async def _refresh_card(
    message: Message, ctx: RequestContext, session: AsyncSession, task: Task
) -> None:
    comments = await TaskService(session).recent_comments(task.id)
    await _edit(message, render_card(ctx.t, task, ctx.today, comments), task_keyboard(ctx.t, task))


async def on_task_action(
    callback: CallbackQuery,
    callback_data: TaskAction,
    session: AsyncSession,
    ctx: RequestContext,
) -> None:
    message = callback.message
    if not isinstance(message, Message):
        await callback.answer()
        return

    service = TaskService(session)
    task = await service.get_by_id(callback_data.task_id)
    # The actor's rights come from the task's workspace, whichever chat the button is in.
    membership = await WorkspaceService(session).require_membership(task.workspace_id, ctx.user.id)
    actor = Actor(user_id=ctx.user.id, role=membership.role)
    action = callback_data.action

    if action in ACTION_TARGETS:
        change = await service.change_status(task.id, actor, ACTION_TARGETS[action])
        await callback.answer()
        await _refresh_card(message, ctx, session, change.task)
        reviewers = await service.workspaces.reviewers(task.workspace_id)
        notice = render_status_change(ctx.t, change, ctx.user, reviewers=reviewers)
        # Editing the card pings nobody, so send a separate notice when someone must act.
        if "tg://user" in notice:
            await message.answer(notice)

    elif action == ACTION_ME:
        added = await service.assign(task.id, actor, [ctx.user])
        if not added:
            raise AppError("already_assigned", number=task.number)
        await callback.answer(ctx.t("toast.assigned_me"))
        await _refresh_card(message, ctx, session, await service.get_by_id(task.id))

    elif action == ACTION_ASSIGN:
        await callback.answer()
        await _show_picker(message, ctx, session, task)

    elif action == ACTION_PRIORITY:
        await service.edit(task.id, actor, TaskPatch(priority=_NEXT_PRIORITY[task.priority]))
        await callback.answer()
        await _refresh_card(message, ctx, session, await service.get_by_id(task.id))

    elif action == ACTION_DELETE_YES:
        await service.soft_delete(task.id, actor)
        await callback.answer()
        await _edit(message, ctx.t("delete.done", number=task.number))

    elif action == ACTION_DELETE_NO:
        await callback.answer()
        await _edit(message, ctx.t("delete.cancelled", number=task.number))

    else:
        await callback.answer()


async def on_list_page(
    callback: CallbackQuery,
    callback_data: ListPage,
    session: AsyncSession,
    ctx: RequestContext,
) -> None:
    message = callback.message
    if not isinstance(message, Message):
        await callback.answer()
        return
    flt, page_number = decode_filter(callback_data)
    await WorkspaceService(session).require_membership(flt.workspace_id, ctx.user.id)

    page = await TaskService(session).list_tasks(flt, page_number, PAGE_SIZE)
    title = await list_title(session, ctx.t, flt)
    await callback.answer()
    await _edit(
        message,
        render_task_list(ctx.t, page, title, ctx.today),
        pagination_keyboard(flt, page.page, page.pages),
    )


async def _show_picker(
    message: Message,
    ctx: RequestContext,
    session: AsyncSession,
    task: Task,
    group_code: int | None = None,
) -> None:
    """Show the card with the picker: groups of the team, or the people of one group."""
    members = await WorkspaceService(session).list_members(task.workspace_id)
    comments = await TaskService(session).recent_comments(task.id)
    if group_code is not None:
        group = from_code(group_code)
        people = [m for m in members if m.specialty == group]
        if people:
            header = ctx.t("picker.group", specialty=specialty_label(ctx.t, group))
            await _edit(
                message,
                render_card(ctx.t, task, ctx.today, comments, header),
                assign_group_keyboard(ctx.t, task, people, group),
            )
            return
    await _edit(
        message,
        render_card(ctx.t, task, ctx.today, comments, ctx.t("picker.menu")),
        assign_menu_keyboard(ctx.t, task, members),
    )


async def on_assign_pick(
    callback: CallbackQuery,
    callback_data: AssignPick,
    session: AsyncSession,
    ctx: RequestContext,
) -> None:
    message = callback.message
    if not isinstance(message, Message):
        await callback.answer()
        return

    service = TaskService(session)
    task = await service.get_by_id(callback_data.task_id)
    membership = await service.workspaces.require_membership(task.workspace_id, ctx.user.id)
    actor = Actor(user_id=ctx.user.id, role=membership.role)
    step = callback_data.step

    if step == "close":
        await callback.answer()
        await _refresh_card(message, ctx, session, task)
    elif step == "menu":
        await callback.answer()
        await _show_picker(message, ctx, session, task)
    elif step == "group":
        await callback.answer()
        await _show_picker(message, ctx, session, task, callback_data.group)
    elif step == "user":
        target = await session.get(User, callback_data.user)
        if target is None:
            raise AppError("task_gone")
        await service.workspaces.require_membership(task.workspace_id, target.id)
        if target.id in {u.id for u in task.assignees}:
            await service.unassign(task.id, actor, [target])
            await callback.answer(ctx.t("toast.unassigned"))
        else:
            await service.assign(task.id, actor, [target])
            await callback.answer()
            if target.id != ctx.user.id:  # editing the card pings nobody: say it in the chat
                await message.answer(ctx.t("notify.assigned", users=mention(target)))
        await _show_picker(message, ctx, session, task, callback_data.group)
    else:
        await callback.answer()


async def on_specialty_pick(
    callback: CallbackQuery,
    callback_data: SpecialtyPick,
    session: AsyncSession,
    ctx: RequestContext,
) -> None:
    """Whoever presses sets *their own* specialty."""
    workspace = ctx.require_workspace()
    specialty = from_code(callback_data.code)
    await WorkspaceService(session).set_specialty(
        workspace.id, ctx.user, specialty, ctx.user.id, ctx.actor.role
    )
    await callback.answer(ctx.t("toast.specialty_saved"))
    if isinstance(callback.message, Message):
        await _edit(
            callback.message,
            ctx.t("specialty.saved", specialty=specialty_label(ctx.t, specialty)),
        )


def register(router: Router) -> None:
    router.callback_query.register(on_task_action, TaskAction.filter())
    router.callback_query.register(on_list_page, ListPage.filter())
    router.callback_query.register(on_assign_pick, AssignPick.filter())
    router.callback_query.register(on_specialty_pick, SpecialtyPick.filter())
