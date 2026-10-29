from __future__ import annotations

from typing import Annotated, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

#: libpq options that asyncpg does not understand and that do not matter for us.
_UNSUPPORTED_QUERY_PARAMS = frozenset({"channel_binding"})


def normalize_database_url(value: str) -> str:
    """Make a provider-style PostgreSQL URL usable with the asyncpg driver.

    * `postgres://` / `postgresql://` get the `+asyncpg` driver.
    * `sslmode=require` (libpq spelling, used by Neon, Supabase, ...) becomes `ssl=require`.
    * `channel_binding=...` is dropped.
    """
    for prefix in ("postgres://", "postgresql://"):
        if value.startswith(prefix):
            value = "postgresql+asyncpg://" + value.removeprefix(prefix)
            break
    if not value.startswith("postgresql+asyncpg://"):
        return value
    parts = urlsplit(value)
    query = [
        ("ssl" if key == "sslmode" else key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if key not in _UNSUPPORTED_QUERY_PARAMS
    ]
    return urlunsplit(parts._replace(query=urlencode(query)))


class DatabaseSettings(BaseSettings):
    """Just the database URL, so migrations can run without a bot token."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./qul_bot.db"

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, value: str) -> str:
        return normalize_database_url(value)


class Settings(DatabaseSettings):
    """Runtime configuration, read from environment variables and an optional `.env` file."""

    bot_token: SecretStr
    allowed_chat_ids: Annotated[list[int], NoDecode] = []
    #: Telegram user ids that are always admins in every workspace (bootstrap / recovery).
    admin_user_ids: Annotated[list[int], NoDecode] = []
    default_timezone: str = "Asia/Tashkent"
    default_locale: str = "uz"
    log_level: str = "INFO"
    #: A self-hosted Telegram Bot API server (https://github.com/tdlib/telegram-bot-api).
    #: The public API only lets bots download files up to 20 MB; a local server allows 2 GB.
    telegram_api_url: str | None = None
    #: Largest app build (.apk/.ipa) the bot will download and inspect.
    max_app_size_mb: int = 20
    #: The AI helper (/ai) is off unless an Anthropic API key is set.
    anthropic_api_key: SecretStr | None = None
    ai_model: str = "claude-opus-5-5"
    #: low | medium | high | xhigh | max: depth of thinking, and so cost and latency.
    ai_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    #: AI requests per workspace per day (a cost guard).
    ai_daily_limit: int = 200

    @field_validator("allowed_chat_ids", "admin_user_ids", mode="before")
    @classmethod
    def _split_id_list(cls, value: object) -> object:
        if isinstance(value, str):
            return [int(part) for part in value.replace(";", ",").split(",") if part.strip()]
        return value

    @field_validator("default_timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown timezone: {value}") from exc
        return value
