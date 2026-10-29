from __future__ import annotations

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from qul_bot.bot import errors
from qul_bot.bot.handlers import admin, callbacks, lists, public, qa, tasks
from qul_bot.bot.middlewares import ContextMiddleware, DbSessionMiddleware
from qul_bot.config import Settings


def create_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )


def create_dispatcher(
    settings: Settings, sessionmaker: async_sessionmaker[AsyncSession]
) -> Dispatcher:
    dp = Dispatcher()
    dp.update.outer_middleware(DbSessionMiddleware(sessionmaker))

    # Everything below `protected` runs behind the context middleware: the chat must be an
    # allowed workspace and the user is resolved before any handler sees the update.
    protected = Router(name="protected")
    context = ContextMiddleware(settings)
    protected.message.middleware(context)
    protected.callback_query.middleware(context)
    # `qa` first: its bug-form handlers must see answers and `/cancel` before anything else.
    for module in (qa, tasks, lists, admin, callbacks):
        router = Router(name=module.__name__.rsplit(".", 1)[-1])
        module.register(router)
        protected.include_router(router)
    shortcuts = Router(name="area-shortcuts")
    lists.register_shortcuts(shortcuts)
    protected.include_router(shortcuts)  # must stay last: it matches any remaining /word

    error_router, public_router = Router(name="errors"), Router(name="public")
    errors.register(error_router)
    public.register(public_router)
    dp.include_routers(error_router, public_router, protected)
    return dp
