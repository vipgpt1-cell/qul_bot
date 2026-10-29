"""The AI helper: turn a discussion into tasks, answer questions about the work, write standups.

The model call sits behind `AIClient`, so the rest of the bot (and the tests) never depend on
the network. `ClaudeClient` is the real implementation (Anthropic Messages API).
"""

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal, Protocol

import anthropic
from anthropic.types.beta import BetaMessageParam, BetaOutputConfigParam
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.db.models import Task, TaskEvent, User
from qul_bot.domain.enums import ACTIVE_STATUSES, EventType, TaskStatus
from qul_bot.errors import AppError
from qul_bot.services.tasks import TaskFilter, TaskService
from qul_bot.services.workspaces import WorkspaceService

MAX_INPUT_CHARS = 12_000
MAX_CONTEXT_TASKS = 200
MAX_EXTRACTED_TASKS = 15

Effort = Literal["low", "medium", "high", "xhigh", "max"]

LANGUAGE_RULE = (
    "Always answer in Uzbek (Latin script), short and concrete, in plain text without "
    "Markdown or HTML. Refer to tasks as #<number>. Use only the data you are given; if it "
    "does not contain the answer, say so."
)


# ---- the model call -------------------------------------------------------------------


class AIClient(Protocol):
    async def complete(
        self, *, system: str, prompt: str, schema: dict[str, Any] | None, max_tokens: int
    ) -> str:
        """The model's text answer (valid JSON when `schema` is given)."""
        ...


class ClaudeClient:
    """Claude via the Anthropic Messages API.

    Requests opt into server-side refusal fallbacks, so a request declined by one model's
    safety classifier is retried on Anthropic's recommended fallback model in the same call.
    """

    def __init__(self, api_key: str, model: str, effort: Effort, timeout: float = 90.0) -> None:
        self.client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=2)
        self.model = model
        self.effort = effort

    async def complete(
        self, *, system: str, prompt: str, schema: dict[str, Any] | None, max_tokens: int
    ) -> str:
        output_config: BetaOutputConfigParam = {"effort": self.effort}
        if schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        messages: list[BetaMessageParam] = [{"role": "user", "content": prompt}]
        try:
            response = await self.client.beta.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                output_config=output_config,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            raise AppError("ai_misconfigured") from exc
        except (
            anthropic.RateLimitError,
            anthropic.OverloadedError,
            anthropic.InternalServerError,
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
        ) as exc:
            raise AppError("ai_busy") from exc
        except anthropic.APIStatusError as exc:
            raise AppError("ai_failed") from exc
        if response.stop_reason == "refusal":
            raise AppError("ai_refused")
        if response.stop_reason == "max_tokens" and schema is not None:
            raise AppError("ai_failed")  # truncated JSON is not usable
        return "".join(block.text for block in response.content if block.type == "text")


# ---- limits ---------------------------------------------------------------------------


@dataclass
class UsageGuard:
    """Per-user cooldown and per-workspace daily cap, in memory (reset on restart)."""

    daily_limit: int
    cooldown_seconds: float = 8.0
    _last_call: dict[int, float] = field(default_factory=dict)
    _daily: dict[tuple[int, date], int] = field(default_factory=dict)

    def check(self, workspace_id: int, user_id: int, today: date) -> None:
        now = time.monotonic()
        if now - self._last_call.get(user_id, -1e9) < self.cooldown_seconds:
            raise AppError("ai_slow_down")
        if self._daily.get((workspace_id, today), 0) >= self.daily_limit:
            raise AppError("ai_daily_limit", limit=self.daily_limit)
        self._last_call[user_id] = now
        self._daily[(workspace_id, today)] = self._daily.get((workspace_id, today), 0) + 1


# ---- results --------------------------------------------------------------------------


class ProposedTask(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: Literal["urgent", "high", "normal", "low"] | None = None
    assignee: str | None = None  # a Telegram username from the team list, without "@"
    due: str | None = None  # "ertaga", "juma", "25.10", ...


class Extraction(BaseModel):
    summary: str
    tasks: list[ProposedTask] = Field(default_factory=list, max_length=MAX_EXTRACTED_TASKS)


_NULLABLE_STRING = {"type": ["string", "null"]}
EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": _NULLABLE_STRING,
                    "priority": {
                        "type": ["string", "null"],
                        "enum": ["urgent", "high", "normal", "low", None],
                    },
                    "assignee": _NULLABLE_STRING,
                    "due": _NULLABLE_STRING,
                },
                "required": ["title", "description", "priority", "assignee", "due"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "tasks"],
    "additionalProperties": False,
}

EXTRACT_SYSTEM = (
    "You are the task assistant of a software team's Telegram group. Read the discussion and "
    "extract concrete, actionable work items: each with a short imperative title, an optional "
    "description with the useful details, a priority only when the text implies one, an "
    "assignee only when a person from the team list is clearly meant (their username, without "
    "@), and a due date only when one is stated (copy it as said, e.g. 'ertaga', 'juma', "
    "'25.10'). Do not invent work that is not in the text; an empty list is fine. Also write a "
    "two- or three-sentence summary of the discussion. Write titles, descriptions and the "
    "summary in Uzbek (Latin script)."
)
ANSWER_SYSTEM = (
    "You are the task assistant of a software team. You get the team's task board as JSON "
    "and a question from a team member. Answer the question from the board. " + LANGUAGE_RULE
)
STANDUP_SYSTEM = (
    "You are the task assistant of a software team. From the task board JSON, write today's "
    "standup for the team chat: what was finished since the last working day, what is in "
    "progress (by person), what waits for review or testing, what is blocked or overdue, and "
    "one line on the biggest risk. Keep it under 15 lines. " + LANGUAGE_RULE
)


# ---- context --------------------------------------------------------------------------


def _task_json(task: Task, today: date) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "number": task.number,
        "title": task.title,
        "status": task.status.value,
        "priority": task.priority.value,
        "kind": task.kind.value,
        "assignees": [u.username or u.display_name for u in task.assignees],
    }
    if task.area:
        entry["area"] = task.area.slug
    if task.due_date:
        entry["due"] = task.due_date.isoformat()
        entry["overdue"] = task.due_date < today and task.status in ACTIVE_STATUSES
    if task.release:
        entry["release"] = task.release
    return entry


class AIService:
    def __init__(self, session: AsyncSession, client: AIClient) -> None:
        self.session = session
        self.client = client
        self.tasks = TaskService(session)
        self.workspaces = WorkspaceService(session)

    async def _team(self, workspace_id: int) -> list[dict[str, Any]]:
        members = await self.workspaces.list_members(workspace_id)
        return [
            {
                "username": m.user.username,
                "name": m.user.display_name,
                "role": m.role.value,
                "specialty": m.specialty.value if m.specialty else None,
            }
            for m in members
        ]

    async def board(self, workspace_id: int, today: date) -> dict[str, Any]:
        """What the model sees: the team, open work, and work finished in the last week."""
        page = await self.tasks.list_tasks(
            TaskFilter(workspace_id=workspace_id), page_size=MAX_CONTEXT_TASKS
        )
        since = datetime.combine(today - timedelta(days=7), datetime.min.time(), tzinfo=UTC)
        finished = await self.session.execute(
            select(Task)
            .where(
                Task.workspace_id == workspace_id,
                Task.deleted_at.is_(None),
                Task.status == TaskStatus.DONE,
                Task.completed_at >= since,
            )
            .order_by(Task.completed_at.desc())
            .limit(50)
        )
        return {
            "today": today.isoformat(),
            "team": await self._team(workspace_id),
            "open_tasks": [_task_json(t, today) for t in page.items],
            "done_last_7_days": [
                {**_task_json(t, today), "completed": t.completed_at.date().isoformat()}
                for t in finished.scalars().all()
                if t.completed_at
            ],
        }

    async def extract_tasks(self, workspace_id: int, text: str) -> Extraction:
        text = text.strip()
        if len(text) < 10:
            raise AppError("ai_nothing_to_read")
        team = await self._team(workspace_id)
        prompt = (
            f"Team:\n{json.dumps(team, ensure_ascii=False)}\n\n"
            f"Discussion:\n<discussion>\n{text[:MAX_INPUT_CHARS]}\n</discussion>"
        )
        raw = await self.client.complete(
            system=EXTRACT_SYSTEM, prompt=prompt, schema=EXTRACTION_SCHEMA, max_tokens=8000
        )
        try:
            result = Extraction.model_validate_json(raw)
        except ValidationError as exc:
            raise AppError("ai_failed") from exc
        result.tasks = result.tasks[:MAX_EXTRACTED_TASKS]
        return result

    async def answer(self, workspace_id: int, question: str, today: date) -> str:
        board = await self.board(workspace_id, today)
        prompt = (
            f"Board:\n{json.dumps(board, ensure_ascii=False)}\n\n"
            f"Question:\n{question.strip()[:2000]}"
        )
        return await self.client.complete(
            system=ANSWER_SYSTEM, prompt=prompt, schema=None, max_tokens=4000
        )

    async def standup(self, workspace_id: int, today: date) -> str:
        board = await self.board(workspace_id, today)
        recent = await self._recent_activity(workspace_id, today)
        prompt = (
            f"Board:\n{json.dumps(board, ensure_ascii=False)}\n\n"
            f"Status changes in the last 3 days:\n{json.dumps(recent, ensure_ascii=False)}"
        )
        return await self.client.complete(
            system=STANDUP_SYSTEM, prompt=prompt, schema=None, max_tokens=4000
        )

    async def _recent_activity(self, workspace_id: int, today: date) -> list[dict[str, Any]]:
        since = datetime.combine(today - timedelta(days=3), datetime.min.time(), tzinfo=UTC)
        result = await self.session.execute(
            select(TaskEvent, Task.number)
            .join(Task, Task.id == TaskEvent.task_id)
            .where(
                TaskEvent.workspace_id == workspace_id,
                TaskEvent.type == EventType.STATUS_CHANGED,
                TaskEvent.created_at >= since,
            )
            .order_by(TaskEvent.id.desc())
            .limit(100)
        )
        return [
            {
                "task": number,
                "from": event.data.get("source"),
                "to": event.data.get("target"),
                "by": event.actor.display_name if event.actor else None,
                "at": event.created_at.isoformat(timespec="minutes"),
            }
            for event, number in result.all()
        ]


def known_usernames(members: Sequence[User]) -> set[str]:
    return {u.username.lower() for u in members if u.username}
