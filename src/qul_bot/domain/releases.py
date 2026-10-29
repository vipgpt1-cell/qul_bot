"""Release (version) labels on tasks: `v:1.4.0`."""

from __future__ import annotations

import re

from qul_bot.errors import InputError

_RELEASE_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]{0,31}$")


def normalize_release(raw: str) -> str:
    """`v1.4.0`, `V1.4.0` and `1.4.0` are the same release: `1.4.0`."""
    value = raw.strip()
    if len(value) > 1 and value[0] in "vV" and value[1].isdigit():
        value = value[1:]
    if not _RELEASE_RE.match(value):
        raise InputError("bad_release", value=raw.strip()[:40])
    return value.lower()
