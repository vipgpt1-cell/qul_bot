"""App build reports: send an .apk or .ipa; get version, SDKs, signing, permissions, red flags."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Document, Message
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.apps.apk import NotAnApp
from qul_bot.apps.ipa import inspect_build
from qul_bot.bot.context import RequestContext
from qul_bot.bot.errors import error_text
from qul_bot.bot.formatting import render_app_report
from qul_bot.bot.handlers.helpers import safe_edit
from qul_bot.config import Settings
from qul_bot.domain.releases import normalize_release
from qul_bot.errors import AppError, InputError
from qul_bot.services.tasks import TaskService

log = logging.getLogger(__name__)

BUILD_EXTENSIONS = (".apk", ".ipa")
INSPECT_TIMEOUT_SECONDS = 60


def _build_document(message: Message) -> Document | None:
    """The build attached to this message (caption command) or to the replied message."""
    for candidate in (message, message.reply_to_message):
        if candidate is not None and candidate.document is not None:
            return candidate.document
    return None


async def _release_tasks(session: AsyncSession, ctx: RequestContext, version: str | None) -> int:
    if ctx.workspace is None or not version:
        return 0
    try:
        release = normalize_release(version)
    except InputError:
        return 0
    for name, total, _ in await TaskService(session).releases(ctx.workspace.id):
        if name == release:
            return total
    return 0


async def report_build(
    message: Message,
    document: Document,
    session: AsyncSession,
    ctx: RequestContext,
    bot: Bot,
    settings: Settings,
) -> None:
    ctx.require_workspace()  # only for members: inspecting files costs server time
    name = document.file_name or ""
    lowered = name.lower()
    if lowered.endswith(".aab"):
        raise InputError("app_aab")
    if not lowered.endswith(BUILD_EXTENSIONS):
        raise InputError("app_unsupported")
    limit = settings.max_app_size_mb << 20
    if document.file_size and document.file_size > limit:
        raise InputError("app_too_big", limit=settings.max_app_size_mb)

    status = await message.reply(ctx.t("app.reading"))
    try:
        buffer = await bot.download(document)
        data = buffer.read() if buffer else b""
        if len(data) > limit:
            raise InputError("app_too_big", limit=settings.max_app_size_mb)
        report = await asyncio.wait_for(
            asyncio.to_thread(inspect_build, name, data), INSPECT_TIMEOUT_SECONDS
        )
    except NotAnApp:
        await safe_edit(status, error_text(ctx.t, AppError("app_unreadable")))
        return
    except TimeoutError:
        await safe_edit(status, error_text(ctx.t, AppError("app_timeout")))
        return
    except AppError as error:
        await safe_edit(status, error_text(ctx.t, error))
        return
    release_tasks = await _release_tasks(session, ctx, report.version_name)
    await safe_edit(status, render_app_report(ctx.t, report, name, release_tasks))


async def cmd_app(
    message: Message,
    session: AsyncSession,
    ctx: RequestContext,
    bot: Bot,
    settings: Settings,
) -> None:
    """`/apk` as the caption of a build, or as a reply to a message with one."""
    document = _build_document(message)
    if document is None:
        raise InputError("app_usage")
    await report_build(message, document, session, ctx, bot, settings)


async def on_private_build(
    message: Message,
    session: AsyncSession,
    ctx: RequestContext,
    bot: Bot,
    settings: Settings,
) -> None:
    """In a private chat, any .apk/.ipa sent to the bot gets a report."""
    assert message.document is not None
    await report_build(message, message.document, session, ctx, bot, settings)


def _is_build(document: Document | None) -> bool:
    name = (document.file_name or "").lower() if document else ""
    return name.endswith((*BUILD_EXTENSIONS, ".aab"))


def register(router: Router) -> None:
    router.message.register(cmd_app, Command("apk", "app", "build", ignore_case=True))
    router.message.register(
        on_private_build,
        F.chat.type == ChatType.PRIVATE,
        F.document.func(_is_build),
    )
