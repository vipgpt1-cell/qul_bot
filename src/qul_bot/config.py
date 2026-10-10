from __future__ import annotations

from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Just the database URL, so migrations can run without a bot token."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./qul_bot.db"

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, value: str) -> str:
        """Hosting providers hand out `postgres://` / `postgresql://`; we need an async driver."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+asyncpg://" + value.removeprefix(prefix)
        return value


class Settings(DatabaseSettings):
    """Runtime configuration, read from environment variables and an optional `.env` file."""

    bot_token: SecretStr
    allowed_chat_ids: Annotated[list[int], NoDecode] = []
    #: Telegram user ids that are always admins in every workspace (bootstrap / recovery).
    admin_user_ids: Annotated[list[int], NoDecode] = []
    default_timezone: str = "Asia/Tashkent"
    default_locale: str = "uz"
    log_level: str = "INFO"

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
