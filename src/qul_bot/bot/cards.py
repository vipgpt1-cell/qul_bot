"""Task cards with everything they show, loaded in one place."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.bot.formatting import render_card
from qul_bot.db.models import Task
from qul_bot.i18n import Translator
from qul_bot.services.tasks import TaskService


async def card_text(
    session: AsyncSession, t: Translator, task: Task, today: date, header: str | None = None
) -> str:
    service = TaskService(session)
    return render_card(
        t,
        task,
        today,
        await service.recent_comments(task.id),
        header,
        checks=await service.checklist_progress(task.id),
        attachments=len(await service.attachments(task.id)),
    )
