"""When the automatic daily digest is due. Pure rules; no clock, no I/O."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

from qul_bot.errors import InputError

#: Monday = 0 ... Sunday = 6. The digest is posted on working days only.
WORKDAYS = frozenset({0, 1, 2, 3, 4})
#: If the bot was down at the scheduled time, it still posts for this long afterwards;
#: a "morning digest" arriving in the evening would only be noise.
GRACE = timedelta(hours=3)
DEFAULT_DIGEST_TIME = "09:00"

_CLOCK_RE = re.compile(r"^(\d{1,2})[:.](\d{2})$")


def parse_clock(text: str) -> time:
    """`9:00`, `09:00` or `9.30` -> time. Raises `InputError("bad_time")`."""
    match = _CLOCK_RE.match(text.strip())
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if hour < 24 and minute < 60:
            return time(hour, minute)
    raise InputError("bad_time", value=text.strip())


def format_clock(value: time) -> str:
    return value.strftime("%H:%M")


def is_digest_due(
    *, enabled: bool, local_now: datetime, at: time, last_sent_on: date | None
) -> bool:
    """Is it time to post today's digest? `local_now` must be in the workspace timezone."""
    if not enabled or local_now.weekday() not in WORKDAYS:
        return False
    if last_sent_on == local_now.date():
        return False
    scheduled = datetime.combine(local_now.date(), at, tzinfo=local_now.tzinfo)
    return scheduled <= local_now < scheduled + GRACE
