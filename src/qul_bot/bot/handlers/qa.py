"""Quality assurance: bug reports, test checklists, releases and the QA step."""

from __future__ import annotations

import re
from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, ForceReply, Message, ReplyParameters
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.bot.callbacks import BugSeverity, CheckToggle
from qul_bot.bot.context import RequestContext, actor_for
from qul_bot.bot.formatting import (
    esc,
    render_checklist,
    render_release_list,
    render_release_report,
    user_name,
)
from qul_bot.bot.handlers.helpers import (
    require_admin,
    resolve_ref,
    resolve_usernames,
    safe_edit,
)
from qul_bot.bot.handlers.lists import build_filter, send_list
from qul_bot.bot.handlers.tasks import answer_card
from qul_bot.bot.keyboards import checklist_keyboard, severity_keyboard
from qul_bot.db.models import ChecklistItem, Task
from qul_bot.domain.enums import Priority, TaskKind
from qul_bot.errors import InputError, NotFoundError
from qul_bot.i18n import Translator
from qul_bot.parsing.task_input import normalize_apostrophes, parse_list_input, parse_task_input
from qul_bot.services.tasks import NewTask, TaskService
from qul_bot.services.workspaces import WorkspaceService

SEVERITY_PRIORITY: dict[str, Priority] = {
    "critical": Priority.URGENT,
    "major": Priority.HIGH,
    "minor": Priority.NORMAL,
    "trivial": Priority.LOW,
}
SKIP = "-"


# ---- the /bug form --------------------------------------------------------------------


class BugForm(StatesGroup):
    """A guided bug report. In groups each question is a reply-forcing message: with privacy
    mode on, the bot only sees replies to its own messages."""

    title = State()
    steps = State()
    expected = State()
    actual = State()
    device = State()
    severity = State()
    screenshot = State()


#: Text questions in order: (state, field, i18n key of the question).
_TEXT_STEPS: tuple[tuple[State, str, str], ...] = (
    (BugForm.title, "title", "bug.ask.title"),
    (BugForm.steps, "steps", "bug.ask.steps"),
    (BugForm.expected, "expected", "bug.ask.expected"),
    (BugForm.actual, "actual", "bug.ask.actual"),
    (BugForm.device, "device", "bug.ask.device"),
)


async def _ask(bot: Bot, chat_id: int, reply_to: int, text: str) -> None:
    """Ask the user a question their Telegram app opens a reply box for."""
    await bot.send_message(
        chat_id,
        text,
        reply_parameters=ReplyParameters(message_id=reply_to, allow_sending_without_reply=True),
        reply_markup=ForceReply(selective=True),
    )


def bug_description(t: Translator, data: dict[str, Any]) -> str:
    """Plain-text description of a bug from the form answers (skipped answers are left out)."""
    parts: list[str] = []
    if data.get("steps"):
        parts.append(f"{t('bug.field.steps')}:\n{data['steps']}")
    for field in ("expected", "actual", "device"):
        if data.get(field):
            parts.append(f"{t(f'bug.field.{field}')}: {data[field]}")
    if data.get("extra"):
        parts.append(str(data["extra"]))
    return "\n\n".join(parts)


async def _create_bug(
    message: Message,
    session: AsyncSession,
    ctx: RequestContext,
    data: dict[str, Any],
    screenshot: tuple[str, str] | None = None,
) -> None:
    workspace = ctx.require_workspace()
    service = TaskService(session)
    task = await service.create(
        workspace,
        ctx.user,
        NewTask(
            title=str(data["title"]),
            description=bug_description(ctx.t, data) or None,
            area_slug=data.get("area"),
            priority=Priority(data.get("priority") or Priority.NORMAL.value),
            assignee_usernames=list(data.get("assignees") or []),
            release=data.get("release"),
            kind=TaskKind.BUG,
        ),
    )
    if screenshot:
        kind, file_id = screenshot
        await service.add_attachment(task.id, ctx.user.id, kind, file_id)
    footer = None if task.assignees else ctx.t("bug.assign_hint")
    await answer_card(message, ctx, session, task, header=ctx.t("bug.created"), footer=footer)


async def cmd_bug(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    ctx: RequestContext,
    state: FSMContext,
    bot: Bot,
) -> None:
    """`/bug` starts the guided form; `/bug Title` skips the first question; a multi-line
    `/bug Title\\n details...` creates the bug at once."""
    workspace = ctx.require_workspace()
    parsed = parse_task_input(command.args or "", ctx.today)
    # Validate tokens now, not after five questions.
    if parsed.area and not await WorkspaceService(session).get_area(workspace.id, parsed.area):
        raise NotFoundError("unknown_area", slug=parsed.area)
    await resolve_usernames(session, ctx, parsed.assignees)

    data: dict[str, Any] = {
        "title": parsed.title,
        "area": parsed.area,
        "priority": parsed.priority.value if parsed.priority else None,
        "assignees": parsed.assignees,
        "release": parsed.release,
    }
    if parsed.title and parsed.description:
        await state.clear()
        await _create_bug(message, session, ctx, {**data, "extra": parsed.description})
        return

    await state.set_data(data)
    first = 1 if parsed.title else 0
    next_state, _, question = _TEXT_STEPS[first]
    await state.set_state(next_state)
    intro = ctx.t("bug.intro")
    await _ask(bot, message.chat.id, message.message_id, f"{intro}\n\n{ctx.t(question)}")


async def on_bug_text(message: Message, ctx: RequestContext, state: FSMContext, bot: Bot) -> None:
    """An answer to one of the text questions."""
    current = await state.get_state()
    index = next(i for i, (s, _, _) in enumerate(_TEXT_STEPS) if s.state == current)
    _, field, _ = _TEXT_STEPS[index]
    answer = (message.text or "").strip()
    if field == "title":
        if not answer or answer == SKIP:
            await _ask(bot, message.chat.id, message.message_id, ctx.t("bug.ask.title"))
            return
        answer = answer[:200]
    await state.update_data({field: None if answer == SKIP else answer[:1500]})

    if index + 1 < len(_TEXT_STEPS):
        next_state, _, question = _TEXT_STEPS[index + 1]
        await state.set_state(next_state)
        await _ask(bot, message.chat.id, message.message_id, ctx.t(question))
    else:
        await state.set_state(BugForm.severity)
        await state.update_data({"reply_to": message.message_id})
        await message.reply(ctx.t("bug.ask.severity"), reply_markup=severity_keyboard(ctx.t))


async def on_bug_severity(
    callback: CallbackQuery,
    callback_data: BugSeverity,
    ctx: RequestContext,
    state: FSMContext,
    bot: Bot,
) -> None:
    if callback_data.level not in SEVERITY_PRIORITY or not isinstance(callback.message, Message):
        await callback.answer()
        return
    data = await state.update_data({"priority": SEVERITY_PRIORITY[callback_data.level].value})
    await state.set_state(BugForm.screenshot)
    await callback.answer()
    chosen = ctx.t(f"bug.severity.{callback_data.level}")
    await safe_edit(callback.message, ctx.t("bug.severity_chosen", severity=chosen))
    await _ask(
        bot,
        callback.message.chat.id,
        int(data.get("reply_to") or callback.message.message_id),
        ctx.t("bug.ask.screenshot"),
    )


async def on_foreign_severity(callback: CallbackQuery, ctx: RequestContext) -> None:
    """Someone pressed a severity button of another person's form."""
    await callback.answer(ctx.t("bug.not_your_form"), show_alert=True)


async def on_bug_screenshot(
    message: Message, session: AsyncSession, ctx: RequestContext, state: FSMContext
) -> None:
    screenshot: tuple[str, str] | None = None
    if message.photo:
        screenshot = ("photo", message.photo[-1].file_id)
    elif message.document:
        screenshot = ("document", message.document.file_id)
    elif (message.text or "").strip() != SKIP:
        await message.reply(ctx.t("bug.ask.screenshot"), reply_markup=ForceReply(selective=True))
        return
    data = await state.get_data()
    await state.clear()
    await _create_bug(message, session, ctx, data, screenshot)


async def cmd_cancel_form(message: Message, ctx: RequestContext, state: FSMContext) -> None:
    """`/cancel` (without a number) while filling in the bug form."""
    await state.clear()
    await message.reply(ctx.t("bug.cancelled"))


async def cmd_bugs(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    parsed = parse_list_input(command.args or "")
    flt = await build_filter(session, ctx, parsed, kind=TaskKind.BUG)
    await send_list(message, session, ctx, flt)


# ---- checklists -----------------------------------------------------------------------


async def send_checklist(
    message: Message, session: AsyncSession, ctx: RequestContext, task: Task
) -> None:
    items = await TaskService(session).checklist(task.id)
    await message.answer(
        render_checklist(ctx.t, task, items), reply_markup=checklist_keyboard(items)
    )


_REMOVE_RE = re.compile(r"^-(\d{1,3})$")


async def cmd_check(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    """`/check 12` shows it, `/check 12 first; second` adds, `/check 12 -2` removes item 2."""
    workspace = ctx.require_workspace()
    number, rest = resolve_ref(message, command.args)
    service = TaskService(session)
    task = await service.get(workspace.id, number)
    if match := _REMOVE_RE.match(rest):
        await service.remove_check(task.id, ctx.actor, int(match.group(1)))
    elif rest:
        await service.add_checks(task.id, ctx.actor, re.split(r"[;\n]", rest))
    await send_checklist(message, session, ctx, task)


async def on_check_toggle(
    callback: CallbackQuery,
    callback_data: CheckToggle,
    session: AsyncSession,
    ctx: RequestContext,
) -> None:
    item = await session.get(ChecklistItem, callback_data.item_id)
    if item is None or not isinstance(callback.message, Message):
        raise NotFoundError("check_not_found", number=0)
    service = TaskService(session)
    task = await service.get_by_id(item.task_id)
    membership = await service.workspaces.require_membership(task.workspace_id, ctx.user.id)
    await service.toggle_check(item.id, actor_for(ctx.user.id, membership))
    items = await service.checklist(task.id)
    await callback.answer()
    await safe_edit(
        callback.message, render_checklist(ctx.t, task, items), checklist_keyboard(items)
    )


# ---- releases, QA settings, files -----------------------------------------------------


async def cmd_release(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    """`/release` lists releases; `/release 1.4.0` is the readiness report."""
    workspace = ctx.require_workspace()
    service = TaskService(session)
    arg = (command.args or "").strip()
    if not arg:
        await message.answer(render_release_list(ctx.t, await service.releases(workspace.id)))
        return
    report = await service.release_report(workspace.id, arg)
    await message.answer(render_release_report(ctx.t, report, ctx.today))


async def cmd_qa(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    """`/qa` shows the testing step's state; `/qa on|off` (admin) switches it."""
    workspace = ctx.require_workspace()
    arg = normalize_apostrophes((command.args or "").strip()).lower()
    workspaces = WorkspaceService(session)
    if arg:
        require_admin(ctx)
        if arg not in ("on", "off"):
            raise InputError("qa_usage")
        await workspaces.configure_qa(workspace, enabled=arg == "on")
    testers = await workspaces.testers(workspace.id)
    if not workspace.qa_enabled:
        text = ctx.t("qa.off")
    elif testers:
        text = ctx.t("qa.on", users=", ".join(user_name(u) for u in testers))
    else:
        text = ctx.t("qa.no_testers")
    await message.answer(f"{text}\n\n{ctx.t('qa.hint')}")


async def cmd_files(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    ctx: RequestContext,
    bot: Bot,
) -> None:
    workspace = ctx.require_workspace()
    number, _ = resolve_ref(message, command.args)
    service = TaskService(session)
    task = await service.get(workspace.id, number)
    files = await service.attachments(task.id)
    if not files:
        await message.answer(ctx.t("files.none", number=task.number))
        return
    caption = ctx.t("files.caption", number=task.number, title=esc(task.title[:80]))
    for attachment in files[:10]:
        if attachment.kind == "photo":
            await bot.send_photo(message.chat.id, attachment.file_id, caption=caption)
        else:
            await bot.send_document(message.chat.id, attachment.file_id, caption=caption)


async def on_checks_button(
    callback: CallbackQuery, session: AsyncSession, ctx: RequestContext, task_id: int
) -> None:
    """The ☑️ button on a task card (dispatched from the task-card handler)."""
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    task = await TaskService(session).get_by_id(task_id)
    await callback.answer()
    await send_checklist(callback.message, session, ctx, task)


def register(router: Router) -> None:
    # The form's handlers come first so its answers and `/cancel` win over other handlers.
    router.message.register(
        cmd_cancel_form, StateFilter(BugForm), F.text.regexp(r"^/cancel(@\w+)?\s*$")
    )
    router.message.register(
        on_bug_text,
        StateFilter(*(s for s, _, _ in _TEXT_STEPS)),
        F.text,
        ~F.text.startswith("/"),
    )
    router.message.register(
        on_bug_screenshot,
        StateFilter(BugForm.screenshot),
        F.photo | F.document | (F.text & ~F.text.startswith("/")),
    )
    router.callback_query.register(
        on_bug_severity, StateFilter(BugForm.severity), BugSeverity.filter()
    )
    router.callback_query.register(on_foreign_severity, BugSeverity.filter())
    router.callback_query.register(on_check_toggle, CheckToggle.filter())
    router.message.register(cmd_bug, Command("bug", ignore_case=True))
    router.message.register(cmd_bugs, Command("bugs", ignore_case=True))
    router.message.register(cmd_check, Command("check", ignore_case=True))
    router.message.register(cmd_release, Command("release", ignore_case=True))
    router.message.register(cmd_qa, Command("qa", ignore_case=True))
    router.message.register(cmd_files, Command("files", ignore_case=True))
