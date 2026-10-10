"""Deadline parsing: `ertaga`, `juma`, `3d`, `25.10`, `2026-10-25`, ..."""

from __future__ import annotations

import re
from datetime import date, timedelta

from qul_bot.errors import InputError

CLEAR_WORDS = frozenset({"-", "none", "no", "yoq", "yo'q", "yo‘q", "yo’q"})

_RELATIVE_DAYS = {
    "bugun": 0,
    "today": 0,
    "ertaga": 1,
    "tomorrow": 1,
    "indinga": 2,
}

# Monday = 0 ... Sunday = 6
_WEEKDAYS: dict[str, int] = {}
for _index, _names in enumerate(
    [
        ("dushanba", "du", "mon", "monday"),
        ("seshanba", "se", "tue", "tuesday"),
        ("chorshanba", "chor", "wed", "wednesday"),
        ("payshanba", "pay", "thu", "thursday"),
        ("juma", "ju", "fri", "friday"),
        ("shanba", "sha", "sat", "saturday"),
        ("yakshanba", "yak", "sun", "sunday"),
    ]
):
    for _name in _names:
        _WEEKDAYS[_name] = _index

_OFFSET_RE = re.compile(r"^\+?(\d{1,3})([dw])$")
_ISO_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_DMY_RE = re.compile(r"^(\d{1,2})[./](\d{1,2})(?:[./](\d{4}))?$")


def is_clear(value: str) -> bool:
    return value.strip().lower() in CLEAR_WORDS


def parse_due(value: str, today: date) -> date:
    """Parse a deadline relative to `today` (in the workspace's timezone).

    A bare weekday means its *next* occurrence ("juma" said on a Friday is next Friday; use
    "bugun" for today). `dd.mm` rolls into next year when that date has already passed.
    Raises `InputError("invalid_due")` for anything unrecognised or in the past.
    """
    raw = value.strip().lower()
    if not raw:
        raise InputError("invalid_due", value=value)

    if raw in _RELATIVE_DAYS:
        return today + timedelta(days=_RELATIVE_DAYS[raw])

    if raw in _WEEKDAYS:
        ahead = (_WEEKDAYS[raw] - today.weekday()) % 7 or 7
        return today + timedelta(days=ahead)

    if match := _OFFSET_RE.match(raw):
        amount = int(match.group(1))
        return today + timedelta(days=amount * (7 if match.group(2) == "w" else 1))

    try:
        if match := _ISO_RE.match(raw):
            parsed = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        elif match := _DMY_RE.match(raw):
            day, month = int(match.group(1)), int(match.group(2))
            if match.group(3):
                parsed = date(int(match.group(3)), month, day)
            else:
                parsed = date(today.year, month, day)
                if parsed < today:
                    parsed = date(today.year + 1, month, day)
        else:
            raise InputError("invalid_due", value=value)
    except ValueError:
        raise InputError("invalid_due", value=value) from None

    if parsed < today:
        raise InputError("due_in_past", value=value)
    return parsed
