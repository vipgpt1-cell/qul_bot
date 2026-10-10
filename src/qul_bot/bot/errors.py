from __future__ import annotations

import logging
import re

from aiogram import Router
from aiogram.filters import ExceptionTypeFilter
from aiogram.types import ErrorEvent

from qul_bot.errors import AppError
from qul_bot.i18n import DEFAULT_LOCALE, Translator

log = logging.getLogger(__name__)


_STATUS_PARAMS = ("status", "source", "target")


def error_text(t: Translator, error: AppError) -> str:
    """Translate an error; status codes in its parameters become readable status names."""
    params = dict(error.params)
    for name in _STATUS_PARAMS:
        value = params.get(name)
        if isinstance(value, str):
            params[name] = t(f"status.{value}")
    return t(f"err.{error.code}", **params)


async def _reply(event: ErrorEvent, text: str) -> None:
    update = event.update
    if update.callback_query:
        await update.callback_query.answer(_plain(text), show_alert=True)
    elif update.message:
        await update.message.answer(text)


def _plain(text: str) -> str:
    """Callback alerts do not render HTML and are capped at 200 characters."""
    plain = re.sub(r"<[^>]+>", "", text).replace("&lt;", "<").replace("&gt;", ">")
    return plain[:200]


async def on_app_error(event: ErrorEvent) -> None:
    error = event.exception
    assert isinstance(error, AppError)
    await _reply(event, error_text(Translator(DEFAULT_LOCALE), error))


async def on_unexpected_error(event: ErrorEvent) -> None:
    log.error("Unhandled error while processing update", exc_info=event.exception)
    await _reply(event, Translator(DEFAULT_LOCALE)("err.unexpected"))


def register(router: Router) -> None:
    router.errors.register(on_app_error, ExceptionTypeFilter(AppError))
    router.errors.register(on_unexpected_error)
