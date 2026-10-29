"""/ai: turn a discussion into tasks, answer questions about the board, write the standup."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.bot.callbacks import AIProposalAction
from qul_bot.bot.context import RequestContext
from qul_bot.bot.errors import error_text
from qul_bot.bot.formatting import PRIORITY_EMOJI, esc, truncate
from qul_bot.bot.handlers.helpers import safe_edit
from qul_bot.domain.enums import Priority
from qul_bot.errors import AppError, InputError
from qul_bot.i18n import Translator
from qul_bot.parsing.due import parse_due
from qul_bot.services.ai import AIClient, AIService, ProposedTask, UsageGuard
from qul_bot.services.tasks import NewTask, TaskService

PROPOSAL_TTL_SECONDS = 3600
TASK_WORDS = frozenset({"tasks", "task", "vazifalar", "vazifa"})
STANDUP_WORDS = frozenset({"standup", "xulosa"})


@dataclass
class Proposal:
    workspace_id: int
    user_id: int
    items: list[ProposedTask]
    created: float = field(default_factory=time.monotonic)


class ProposalStore:
    """AI-proposed tasks waiting for a person's confirmation (in memory, one hour)."""

    def __init__(self) -> None:
        self._items: dict[str, Proposal] = {}

    def put(self, proposal: Proposal) -> str:
        self._purge()
        key = secrets.token_hex(6)
        self._items[key] = proposal
        return key

    def get(self, key: str) -> Proposal | None:
        self._purge()
        return self._items.get(key)

    def pop(self, key: str) -> None:
        self._items.pop(key, None)

    def _purge(self) -> None:
        now = time.monotonic()
        for key in [k for k, p in self._items.items() if now - p.created > PROPOSAL_TTL_SECONDS]:
            del self._items[key]


def _render_proposal(t: Translator, summary: str, items: list[ProposedTask]) -> str:
    lines = [t("ai.summary_title"), esc(truncate(summary, 800)), ""]
    if not items:
        lines.append(t("ai.no_tasks"))
        return "\n".join(lines)
    lines.append(t("ai.proposed_title", count=len(items)))
    for n, item in enumerate(items, 1):
        priority = PRIORITY_EMOJI[Priority(item.priority or "normal")]
        extra = []
        if item.assignee:
            extra.append(f"@{esc(item.assignee.lstrip('@'))}")
        if item.due:
            extra.append(f"📅 {esc(item.due)}")
        tail = f" — {' · '.join(extra)}" if extra else ""
        lines.append(f"{n}. {priority} {esc(truncate(item.title, 90))}{tail}")
    return "\n".join(lines)


def _proposal_keyboard(t: Translator, key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn.ai_create_all"),
                    callback_data=AIProposalAction(key=key, action="all").pack(),
                ),
                InlineKeyboardButton(
                    text=t("btn.ai_dismiss"),
                    callback_data=AIProposalAction(key=key, action="no").pack(),
                ),
            ]
        ]
    )


async def cmd_ai(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    ctx: RequestContext,
    ai_client: AIClient | None,
    ai_guard: UsageGuard,
    ai_proposals: ProposalStore,
) -> None:
    workspace = ctx.require_workspace()
    if ai_client is None:
        raise AppError("ai_disabled")
    args = (command.args or "").strip()
    word, _, rest = args.partition(" ")
    sub = word.lower()
    if not args:
        raise InputError("ai_usage")

    source = message.reply_to_message
    quoted = (source.text or source.caption or "") if source else ""
    if sub in TASK_WORDS and not (rest.strip() or quoted.strip()):
        raise InputError("ai_usage")

    ai_guard.check(workspace.id, ctx.user.id, ctx.today)
    status = await message.reply(ctx.t("ai.thinking"))
    service = AIService(session, ai_client)
    try:
        if sub in TASK_WORDS:
            text = "\n\n".join(part for part in (quoted.strip(), rest.strip()) if part)
            result = await service.extract_tasks(workspace.id, text)
            body = _render_proposal(ctx.t, result.summary, result.tasks)
            if result.tasks:
                key = ai_proposals.put(Proposal(workspace.id, ctx.user.id, result.tasks))
                await safe_edit(status, body, _proposal_keyboard(ctx.t, key))
            else:
                await safe_edit(status, body)
            return
        if sub in STANDUP_WORDS:
            answer = await service.standup(workspace.id, ctx.today)
            header = ctx.t("ai.standup_title")
        else:
            answer = await service.answer(workspace.id, args, ctx.today)
            header = ctx.t("ai.answer_title")
    except AppError as error:
        await safe_edit(status, error_text(ctx.t, error))
        return
    await safe_edit(status, f"{header}\n\n{esc(truncate(answer, 3500))}")


async def on_proposal(
    callback: CallbackQuery,
    callback_data: AIProposalAction,
    session: AsyncSession,
    ctx: RequestContext,
    ai_proposals: ProposalStore,
) -> None:
    message = callback.message
    proposal = ai_proposals.get(callback_data.key)
    if proposal is None or not isinstance(message, Message):
        raise AppError("ai_expired")
    if proposal.user_id != ctx.user.id:
        raise AppError("ai_not_yours")

    if callback_data.action != "all":
        ai_proposals.pop(callback_data.key)
        await callback.answer()
        await safe_edit(message, ctx.t("ai.dismissed"))
        return

    workspace = ctx.require_workspace()
    service = TaskService(session)
    created: list[int] = []
    for item in proposal.items:
        assignee = (item.assignee or "").lstrip("@").lower()
        known = assignee and await service.workspaces.find_member_by_username(
            workspace.id, assignee
        )
        try:
            due = parse_due(item.due, ctx.today) if item.due else None
        except InputError:
            due = None  # an unclear date stays in the description rather than failing
        task = await service.create(
            workspace,
            ctx.user,
            NewTask(
                title=item.title,
                description=item.description,
                priority=Priority(item.priority or "normal"),
                assignee_usernames=[assignee] if known else [],
                due=due,
            ),
        )
        created.append(task.number)
    ai_proposals.pop(callback_data.key)
    await callback.answer()
    links = ", ".join(f"/t{n}" for n in created)
    await safe_edit(message, ctx.t("ai.created", count=len(created), links=links))


def register(router: Router) -> None:
    router.message.register(cmd_ai, Command("ai", ignore_case=True))
    router.callback_query.register(on_proposal, AIProposalAction.filter())
