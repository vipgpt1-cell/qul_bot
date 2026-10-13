from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from qul_bot.domain.schedule import format_clock, is_digest_due, parse_clock
from qul_bot.errors import InputError

TASHKENT = ZoneInfo("Asia/Tashkent")
NINE = time(9, 0)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("9:00", time(9, 0)), ("09:00", time(9, 0)), ("9.30", time(9, 30)), ("23:59", time(23, 59))],
)
def test_parse_clock(text: str, expected: time) -> None:
    assert parse_clock(text) == expected


@pytest.mark.parametrize("text", ["", "9", "24:00", "09:60", "nine", "9:5", "ertalab"])
def test_parse_clock_rejects(text: str) -> None:
    with pytest.raises(InputError) as exc:
        parse_clock(text)
    assert exc.value.code == "bad_time"


def test_format_clock() -> None:
    assert format_clock(time(9, 5)) == "09:05"


def due(local: datetime, *, enabled: bool = True, last: date | None = None) -> bool:
    return is_digest_due(enabled=enabled, local_now=local, at=NINE, last_sent_on=last)


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=TASHKENT)  # 13th = Tuesday


def test_due_on_a_working_morning() -> None:
    assert due(at(13, 9, 0))
    assert due(at(13, 9, 40))
    assert due(at(13, 11, 59))


def test_not_before_the_scheduled_time_nor_long_after() -> None:
    assert not due(at(13, 8, 59))
    assert not due(at(13, 12, 0))  # grace window of 3 hours is over
    assert not due(at(13, 18, 0))


def test_not_on_weekends() -> None:
    assert not due(at(10, 9, 0))  # Saturday
    assert not due(at(11, 9, 0))  # Sunday
    assert due(at(12, 9, 0))  # Monday


def test_only_once_per_local_day() -> None:
    assert not due(at(13, 9, 5), last=date(2026, 10, 13))
    assert due(at(13, 9, 5), last=date(2026, 10, 12))


def test_disabled_never_due() -> None:
    assert not due(at(13, 9, 0), enabled=False)
