"""End-to-end build reports through the real dispatcher."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.fake_telegram import Harness
from tests.test_apps import FIXTURES, make_ipa
from tests.test_bot_flow import ADMIN, ALI, STRANGER, build_harness, introduce

DEBUG_APK = ("TestActivity.apk", (FIXTURES / "TestActivity.apk").read_bytes())
SAMPLE_APK = ("app-release.apk", (FIXTURES / "synthetic-v1-target34.apk").read_bytes())


@pytest.fixture
async def h(engine: AsyncEngine, tmp_path: Path) -> AsyncIterator[Harness]:
    harness = build_harness(engine, tmp_path, chat_admins=(ADMIN.id,))
    await introduce(harness)
    yield harness
    await harness.bot.session.close()


async def test_build_with_apk_caption(h: Harness) -> None:
    await h.say(ALI, "/apk", document=DEBUG_APK)
    assert "o'qilmoqda" in h.session.last_text()  # instant feedback while reading
    report = h.session.last_edit()
    assert "TestsAndroguardApplication" in report
    assert "tests.androguard" in report
    assert "debuggable" in report
    assert "Debug kalit" in report
    assert "Android 2.3" in report


async def test_reply_to_a_build_with_apk(h: Harness) -> None:
    upload = await h.say(ALI, "", document=SAMPLE_APK)
    await h.say(ALI, "/apk", reply_to=upload)
    report = h.session.last_edit()
    assert "Qul Sample" in report
    assert "2.1.0" in report
    assert "(42)" in report
    assert "Faqat v1 imzo" in report
    assert "CAMERA" in report
    assert "arm64-v8a" in report


async def test_build_links_to_its_release(h: Harness) -> None:
    await h.say(ALI, "/task Ship sample v:2.1.0")
    await h.say(ALI, "/apk", document=SAMPLE_APK)
    assert "/release 2.1.0" in h.session.last_edit()


async def test_ipa_report(h: Harness) -> None:
    await h.say(ALI, "/apk", document=("Qul.ipa", make_ipa(development=True, devices=2)))
    report = h.session.last_edit()
    assert "Qul iOS" in report
    assert "iOS 15.0" in report
    assert "development" in report
    assert "Development profil" in report


async def test_private_chat_build_needs_no_command(h: Harness) -> None:
    await h.say(ALI, "", document=SAMPLE_APK, chat_id=ALI.id, chat_type="private")
    assert "Qul Sample" in h.session.last_edit()


async def test_strangers_cannot_use_the_inspector(h: Harness) -> None:
    await h.say(STRANGER, "", document=SAMPLE_APK, chat_id=STRANGER.id, chat_type="private")
    assert "guruh" in h.session.last_text()
    assert h.session.edited() == []


async def test_bad_inputs(h: Harness) -> None:
    await h.say(ALI, "/apk")
    assert "/apk" in h.session.last_text() and "izohi bilan" in h.session.last_text()
    await h.say(ALI, "/apk", document=("bundle.aab", b"PK"))
    assert ".aab" in h.session.last_text()
    await h.say(ALI, "/apk", document=("notes.pdf", b"%PDF"))
    assert "Faqat .apk va .ipa" in h.session.last_text()
    await h.say(ALI, "/apk", document=("broken.apk", b"definitely not a zip"))
    assert "o'qib bo'lmadi" in h.session.last_edit()


async def test_size_limit(engine: AsyncEngine, tmp_path: Path) -> None:
    from qul_bot.bot.app import create_dispatcher
    from qul_bot.config import Settings
    from qul_bot.db.session import create_sessionmaker
    from tests.conftest import database_url
    from tests.fake_telegram import GROUP_ID

    harness = build_harness(engine, tmp_path, chat_admins=(ADMIN.id,))
    settings = Settings(
        bot_token="123456:TEST",  # type: ignore[arg-type]
        allowed_chat_ids=[GROUP_ID],
        database_url=database_url(tmp_path),
        max_app_size_mb=0,
    )
    harness.dp = create_dispatcher(settings, create_sessionmaker(engine))
    await introduce(harness)
    await harness.say(ALI, "/apk", document=SAMPLE_APK)
    assert "juda katta" in harness.session.last_text()
    await harness.bot.session.close()
