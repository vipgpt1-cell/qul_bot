"""Areas (`#mobile`, `#backend`, ...) group tasks by team or product part."""

from __future__ import annotations

import re

from qul_bot.errors import InputError

SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{1,19}$")

#: Every bot command name. An area named like a command would be unreachable as `/<area>`.
#: A test keeps this in sync with the registered handlers.
RESERVED_SLUGS = frozenset(
    {
        "start", "help", "chatid", "task", "add", "list", "my", "review", "info", "edit",
        "assign", "unassign", "comment", "delete", "restore", "digest", "doing", "ready",
        "done", "approve", "reject", "block", "reopen", "cancel", "areas", "addarea",
        "delarea", "team", "role", "specialty", "find", "history", "bug", "bugs", "check",
        "release", "qa", "files", "apk", "app", "build", "ai", "all",
    }
)  # fmt: skip

_TASK_SHORTCUT_RE = re.compile(r"^t\d+$")


def normalize_slug(raw: str) -> str:
    slug = raw.strip().lstrip("#").lower()
    if not SLUG_RE.match(slug):
        raise InputError("bad_area_slug")
    if slug in RESERVED_SLUGS or _TASK_SHORTCUT_RE.match(slug):
        raise InputError("reserved_area_slug", slug=slug)
    return slug
