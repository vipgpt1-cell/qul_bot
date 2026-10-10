from pathlib import Path

import pytest
from pydantic import ValidationError

from qul_bot.config import DatabaseSettings, Settings


def make(**env: object) -> Settings:
    return Settings(_env_file=None, **env)  # type: ignore[call-arg,arg-type]


def test_chat_ids_accept_comma_separated_text() -> None:
    assert make(bot_token="1:a", allowed_chat_ids="-1001, -1002 ;-1003").allowed_chat_ids == [
        -1001,
        -1002,
        -1003,
    ]


def test_chat_ids_default_to_empty() -> None:
    assert make(bot_token="1:a").allowed_chat_ids == []
    assert make(bot_token="1:a", allowed_chat_ids="").allowed_chat_ids == []


def test_chat_ids_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "-1001234567890")
    monkeypatch.setenv("BOT_TOKEN", "1:a")
    assert Settings(_env_file=None).allowed_chat_ids == [-1001234567890]  # type: ignore[call-arg]


@pytest.mark.parametrize("prefix", ["postgres://", "postgresql://"])
def test_hosting_style_postgres_urls_get_the_async_driver(prefix: str) -> None:
    url = DatabaseSettings(database_url=f"{prefix}u:p@host:5432/db").database_url
    assert url == "postgresql+asyncpg://u:p@host:5432/db"


def test_explicit_driver_is_left_alone() -> None:
    url = "sqlite+aiosqlite:///x.db"
    assert DatabaseSettings(database_url=url).database_url == url


def test_unknown_timezone_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make(bot_token="1:a", default_timezone="Mars/Olympus")


def test_token_is_required_and_hidden() -> None:
    with pytest.raises(ValidationError):
        make()
    assert "1:secret" not in repr(make(bot_token="1:secret"))


def test_admin_user_ids_parse_like_chat_ids() -> None:
    assert make(bot_token="1:a", admin_user_ids="11, 22").admin_user_ids == [11, 22]
    assert make(bot_token="1:a").admin_user_ids == []


def test_missing_token_gives_a_readable_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from qul_bot.__main__ import load_settings

    monkeypatch.chdir(tmp_path)  # no .env here
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exit_info:
        load_settings()
    message = str(exit_info.value)
    assert "BOT_TOKEN" in message
    assert "Traceback" not in message
