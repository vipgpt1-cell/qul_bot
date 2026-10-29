"""A stand-in for the model: records prompts, returns scripted answers."""

from __future__ import annotations

from typing import Any

from qul_bot.errors import AppError


class FakeAIClient:
    def __init__(self, *replies: str | AppError) -> None:
        self.replies = list(replies)
        self.calls: list[dict[str, Any]] = []

    async def complete(
        self, *, system: str, prompt: str, schema: dict[str, Any] | None, max_tokens: int
    ) -> str:
        self.calls.append(
            {"system": system, "prompt": prompt, "schema": schema, "max_tokens": max_tokens}
        )
        reply = self.replies.pop(0) if self.replies else "ok"
        if isinstance(reply, AppError):
            raise reply
        return reply
