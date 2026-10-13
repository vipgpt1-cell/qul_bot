"""Background job: post the daily digest into each workspace on working mornings."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from qul_bot.bot.formatting import render_digest
from qul_bot.i18n import Translator
from qul_bot.services.digests import DigestService
from qul_bot.services.tasks import DIGEST_SECTION_LIMIT, TaskService

log = logging.getLogger(__name__)

TICK_SECONDS = 60.0


async def send_due_digests(
    bot: Bot,
    sessionmaker: async_sessionmaker[AsyncSession],
    now: datetime | None = None,
) -> int:
    """Post the digest to every workspace that is due. Returns how many were posted.

    Workspaces with nothing to report are skipped silently: an empty "all clear" every
    morning is noise. The day is claimed before sending, so a failure never causes duplicates.
    """
    now = now or datetime.now(UTC)
    async with sessionmaker() as session:
        due = await DigestService(session).claim_due(now)
        await session.commit()  # the claim is durable before anything is sent

        posted = 0
        for workspace in due:
            today = now.astimezone(ZoneInfo(workspace.timezone)).date()
            digest = await TaskService(session).digest(workspace.id, today)
            if digest.is_empty or workspace.telegram_chat_id is None:
                continue
            text = render_digest(Translator(workspace.locale), digest, today, DIGEST_SECTION_LIMIT)
            try:
                await bot.send_message(workspace.telegram_chat_id, text)
                posted += 1
            except TelegramAPIError:
                log.exception("Could not post the digest to workspace %s", workspace.id)
        return posted


async def run_scheduler(
    bot: Bot, sessionmaker: async_sessionmaker[AsyncSession], interval: float = TICK_SECONDS
) -> None:
    """Check once a minute whether a digest is due. One failed tick never stops the loop."""
    while True:
        try:
            await send_due_digests(bot, sessionmaker)
        except Exception:
            log.exception("Digest scheduler tick failed")
        await asyncio.sleep(interval)
