from __future__ import annotations

import json
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest

from qul_bot.domain.enums import TaskStatus
from qul_bot.errors import AppError
from qul_bot.services.ai import EXTRACTION_SCHEMA, AIService, ClaudeClient, UsageGuard
from qul_bot.services.tasks import NewTask, TaskService
from tests.conftest import World
from tests.fake_ai import FakeAIClient

TODAY = date(2026, 10, 29)


# ---- the real client, with the SDK call intercepted -----------------------------------


def _message(text: str, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=text),
        ],
    )


def _client(
    monkeypatch: pytest.MonkeyPatch, outcome: Any
) -> tuple[ClaudeClient, list[dict[str, Any]]]:
    client = ClaudeClient("sk-test", "claude-opus-5-5", "medium")
    seen: list[dict[str, Any]] = []

    async def create(**kwargs: Any) -> Any:
        seen.append(kwargs)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(client.client.beta.messages, "create", create)
    return client, seen


def _http_error(cls: type[anthropic.APIStatusError], status: int) -> anthropic.APIStatusError:
    response = httpx2.Response(status, request=httpx2.Request("POST", "https://api.anthropic.com"))
    return cls("boom", response=response, body=None)


async def test_request_shape_with_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    client, seen = _client(monkeypatch, _message('{"summary": "x", "tasks": []}'))
    text = await client.complete(
        system="sys", prompt="hi", schema=EXTRACTION_SCHEMA, max_tokens=8000
    )
    assert text == '{"summary": "x", "tasks": []}'  # thinking blocks are skipped
    [request] = seen
    assert request["model"] == "claude-opus-5-5"
    assert request["fallbacks"] == "default"
    assert request["betas"] == ["server-side-fallback-2026-07-01"]
    assert request["output_config"] == {
        "effort": "medium",
        "format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA},
    }
    assert request["messages"] == [{"role": "user", "content": "hi"}]
    assert "thinking" not in request  # Opus 5.5 thinks adaptively; effort is the control


async def test_plain_text_request_has_no_format(monkeypatch: pytest.MonkeyPatch) -> None:
    client, seen = _client(monkeypatch, _message("javob"))
    assert await client.complete(system="s", prompt="p", schema=None, max_tokens=100) == "javob"
    assert seen[0]["output_config"] == {"effort": "medium"}


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (_http_error(anthropic.RateLimitError, 429), "ai_busy"),
        (_http_error(anthropic.OverloadedError, 529), "ai_busy"),
        (_http_error(anthropic.InternalServerError, 500), "ai_busy"),
        (_http_error(anthropic.AuthenticationError, 401), "ai_misconfigured"),
        (_http_error(anthropic.PermissionDeniedError, 403), "ai_misconfigured"),
        (_http_error(anthropic.BadRequestError, 400), "ai_failed"),
        (anthropic.APIConnectionError(request=httpx2.Request("POST", "https://x")), "ai_busy"),
    ],
)
async def test_errors_become_user_messages(
    monkeypatch: pytest.MonkeyPatch, error: Exception, code: str
) -> None:
    client, _ = _client(monkeypatch, error)
    with pytest.raises(AppError) as raised:
        await client.complete(system="s", prompt="p", schema=None, max_tokens=10)
    assert raised.value.code == code


async def test_refusal_and_truncated_json(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = _client(monkeypatch, _message("", stop_reason="refusal"))
    with pytest.raises(AppError) as refused:
        await client.complete(system="s", prompt="p", schema=None, max_tokens=10)
    assert refused.value.code == "ai_refused"

    client, _ = _client(monkeypatch, _message('{"summary": "cut', stop_reason="max_tokens"))
    with pytest.raises(AppError) as truncated:
        await client.complete(system="s", prompt="p", schema=EXTRACTION_SCHEMA, max_tokens=10)
    assert truncated.value.code == "ai_failed"


def test_schema_is_strict() -> None:
    assert EXTRACTION_SCHEMA["additionalProperties"] is False
    item = EXTRACTION_SCHEMA["properties"]["tasks"]["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == set(item["properties"])


# ---- the service ----------------------------------------------------------------------


async def test_extract_tasks(world: World) -> None:
    reply = json.dumps({
        "summary": "Login bo'yicha muhokama",
        "tasks": [
            {"title": "Login xatosini tuzatish", "description": None, "priority": "high",
             "assignee": "devalisher", "due": "ertaga"},
        ],
    })  # fmt: skip
    fake = FakeAIClient(reply)
    result = await AIService(world.session, fake).extract_tasks(
        world.workspace.id, "Ali, ertaga login xatosini tuzatib qo'y, muhim"
    )
    assert result.summary == "Login bo'yicha muhokama"
    assert [(t.title, t.priority, t.assignee) for t in result.tasks] == [
        ("Login xatosini tuzatish", "high", "devalisher")
    ]
    call = fake.calls[0]
    assert call["schema"] is EXTRACTION_SCHEMA
    assert "devalisher" in call["prompt"]  # the team list is in the prompt
    assert "<discussion>" in call["prompt"]


async def test_extract_rejects_bad_output_and_short_input(world: World) -> None:
    service = AIService(world.session, FakeAIClient('{"summary": 1}'))
    with pytest.raises(AppError) as bad:
        await service.extract_tasks(world.workspace.id, "a long enough discussion text")
    assert bad.value.code == "ai_failed"
    with pytest.raises(AppError) as short:
        await service.extract_tasks(world.workspace.id, "hi")
    assert short.value.code == "ai_nothing_to_read"


async def test_board_and_standup_context(world: World) -> None:
    tasks = TaskService(world.session)
    late = await tasks.create(
        world.workspace, world.dev,
        NewTask(title="Late", due=TODAY - timedelta(days=1), assignee_usernames=["devalisher"]),
    )  # fmt: skip
    shipped = await tasks.create(
        world.workspace, world.dev, NewTask(title="Shipped", assignee_usernames=["devalisher"])
    )
    await tasks.change_status(shipped.id, world.dev_actor, TaskStatus.REVIEW)
    await tasks.change_status(shipped.id, world.reviewer_actor, TaskStatus.DONE)

    service = AIService(world.session, FakeAIClient("standup text"))
    board = await service.board(world.workspace.id, TODAY + timedelta(days=0))
    open_task = next(t for t in board["open_tasks"] if t["number"] == late.number)
    assert open_task["overdue"] is True
    assert open_task["assignees"] == ["devalisher"]
    assert [t["title"] for t in board["done_last_7_days"]] == ["Shipped"]
    assert {m["username"] for m in board["team"]} >= {"devalisher", "reviewer1"}

    fake = FakeAIClient("standup text")
    assert await AIService(world.session, fake).standup(world.workspace.id, TODAY) == "standup text"
    assert '"to": "done"' in fake.calls[0]["prompt"]


def test_usage_guard() -> None:
    guard = UsageGuard(daily_limit=2, cooldown_seconds=0)
    guard.check(1, 10, TODAY)
    guard.check(1, 11, TODAY)
    with pytest.raises(AppError) as limit:
        guard.check(1, 12, TODAY)
    assert limit.value.code == "ai_daily_limit"
    guard.check(1, 12, TODAY + timedelta(days=1))  # a new day
    guard.check(2, 10, TODAY)  # another workspace

    slow = UsageGuard(daily_limit=100, cooldown_seconds=60)
    slow.check(1, 10, TODAY)
    with pytest.raises(AppError) as cooldown:
        slow.check(1, 10, TODAY)
    assert cooldown.value.code == "ai_slow_down"
