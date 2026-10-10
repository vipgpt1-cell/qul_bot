"""Inline-button presses on task cards and list pages."""

from __future__ import annotations

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.bot.callbacks import (
    ACTION_DELETE_NO,
    ACTION_DELETE_YES,
    ACTION_ME,
    ACTION_PRIORITY,
    ACTION_TARGETS,
    ListPage,
    TaskAction,
    decode_filter,
)
from qul_bot.bot.context import RequestContext
from qul_bot.bot.formatting import render_card, render_status_change, render_task_list
from qul_bot.bot.handlers.lists import PAGE_SIZE, list_title
from qul_bot.bot.keyboards import pagination_keyboard, task_keyboard
from qul_bot.db.models import Task
from qul_bot.domain.enums import Priority
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


def register(router: Router) -> None:
    router.callback_query.register(on_task_action, TaskAction.filter())
    router.callback_query.register(on_list_page, ListPage.filter())
