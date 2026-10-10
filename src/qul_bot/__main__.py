from __future__ import annotations

import asyncio
import logging

from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError
from pydantic import ValidationError

from qul_bot.bot.app import create_bot, create_dispatcher
from qul_bot.bot.commands import publish_menus
from qul_bot.config import Settings
from qul_bot.db.session import create_engine, create_sessionmaker
from qul_bot.i18n import Translator

log = logging.getLogger("qul_bot")


def load_settings() -> Settings:
    """Read the configuration, turning validation errors into one readable message."""
    try:
        return Settings()  # type: ignore[call-arg]  # values come from the environment
    except ValidationError as error:
        problems = [
            f"  {'.'.join(str(part) for part in item['loc']).upper()}: {item['msg']}"
            for item in error.errors()
        ]
        raise SystemExit(
            "Invalid configuration (see .env.example):\n" + "\n".join(problems)
        ) from None


async def run() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    if not settings.allowed_chat_ids:
        log.warning(
            "ALLOWED_CHAT_IDS is empty: the bot will only answer /chatid and private messages "
            "until you add your group's id."
        )

    engine = create_engine(settings.database_url)
    bot = create_bot(settings)
    dp = create_dispatcher(settings, create_sessionmaker(engine))
    try:
        try:
            me = await bot.get_me()
        except TelegramUnauthorizedError:
            log.error("Telegram rejected BOT_TOKEN. Check the token from @BotFather.")
            raise SystemExit(1) from None
        except TelegramNetworkError as error:
            log.error("Cannot reach Telegram: %s", error)
            raise SystemExit(1) from None
        log.info("Starting @%s (chats allowed: %s)", me.username, settings.allowed_chat_ids)
        await publish_menus(bot, Translator(settings.default_locale))
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await engine.dispose()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("Stopped")


if __name__ == "__main__":
    main()
