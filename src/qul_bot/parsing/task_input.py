"""Parser for the one-line task grammar.

    /task Fix login crash on iOS #mobile @ali @vali !high muddat:juma

Tokens (all optional, any position):

    #area            area slug              (`#-` clears it when editing)
    @username        assignee (repeatable)
    !priority        urgent | high | normal | low   (also Uzbek: shoshilinch, yuqori, o'rta, past)
    muddat:<when>    deadline; `due:` and `deadline:` work too (`muddat:-` clears it)

Everything else is the title. Extra lines become the description.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from qul_bot.domain.enums import Priority, TaskStatus
from qul_bot.errors import InputError
from qul_bot.parsing.due import is_clear, parse_due

MAX_TITLE_LENGTH = 200

_AREA_RE = re.compile(r"^#([A-Za-z][A-Za-z0-9_]{0,31})$")
_USERNAME_RE = re.compile(r"^@([A-Za-z][A-Za-z0-9_]{4,31})$")
_DUE_RE = re.compile(r"^(?:due|muddat|deadline):(.*)$", re.IGNORECASE)
_APOSTROPHES = str.maketrans({"‘": "'", "’": "'", "ʻ": "'", "ʼ": "'", "`": "'"})

PRIORITY_WORDS: dict[str, Priority] = {
    "urgent": Priority.URGENT,
    "shoshilinch": Priority.URGENT,
    "p0": Priority.URGENT,
    "high": Priority.HIGH,
    "yuqori": Priority.HIGH,
    "p1": Priority.HIGH,
    "normal": Priority.NORMAL,
    "orta": Priority.NORMAL,
    "o'rta": Priority.NORMAL,
    "oddiy": Priority.NORMAL,
    "p2": Priority.NORMAL,
    "low": Priority.LOW,
    "past": Priority.LOW,
    "p3": Priority.LOW,
}

STATUS_WORDS: dict[str, TaskStatus] = {
    "todo": TaskStatus.TODO,
    "kutilmoqda": TaskStatus.TODO,
    "yangi": TaskStatus.TODO,
    "doing": TaskStatus.DOING,
    "jarayonda": TaskStatus.DOING,
    "review": TaskStatus.REVIEW,
    "tekshiruvda": TaskStatus.REVIEW,
    "blocked": TaskStatus.BLOCKED,
    "bloklangan": TaskStatus.BLOCKED,
    "done": TaskStatus.DONE,
    "bajarildi": TaskStatus.DONE,
    "cancelled": TaskStatus.CANCELLED,
    "canceled": TaskStatus.CANCELLED,
    "bekor": TaskStatus.CANCELLED,
}

ALL_WORDS = frozenset({"all", "hammasi"})


def normalize_apostrophes(text: str) -> str:
    return text.translate(_APOSTROPHES)


def _clean(word: str) -> str:
    """Strip list punctuation so `@ali,` is still a mention."""
    return word.rstrip(",;")


def _priority_for(word: str) -> Priority | None:
    return PRIORITY_WORDS.get(normalize_apostrophes(word).lower())


@dataclass(slots=True)
class TaskInput:
    title: str = ""
    description: str = ""
    area: str | None = None
    clear_area: bool = False
    priority: Priority | None = None
    assignees: list[str] = field(default_factory=list)
    due: date | None = None
    clear_due: bool = False


def parse_task_input(text: str, today: date) -> TaskInput:
    """Parse the argument text of /task and /edit."""
    result = TaskInput()
    kept_lines: list[str] = []

    for line in text.strip().splitlines():
        kept_words: list[str] = []
        for word in line.split():
            token = _clean(word)

            if match := _AREA_RE.match(token):
                result.area = match.group(1).lower()
                result.clear_area = False
            elif token == "#-":
                result.area = None
                result.clear_area = True
            elif match := _USERNAME_RE.match(token):
                username = match.group(1).lower()
                if username not in result.assignees:
                    result.assignees.append(username)
            elif token.startswith("!") and (priority := _priority_for(token[1:])):
                result.priority = priority
            elif match := _DUE_RE.match(word):
                value = match.group(1)
                if is_clear(value):
                    result.due = None
                    result.clear_due = True
                else:
                    result.due = parse_due(value, today)
                    result.clear_due = False
            else:
                kept_words.append(word)
        if kept_words:
            kept_lines.append(" ".join(kept_words))

    if kept_lines:
        result.title = kept_lines[0]
        result.description = "\n".join(kept_lines[1:])

    if len(result.title) > MAX_TITLE_LENGTH:
        raise InputError("title_too_long", max=MAX_TITLE_LENGTH)
    return result


@dataclass(slots=True)
class ListInput:
    area: str | None = None
    statuses: set[TaskStatus] = field(default_factory=set)
    priority: Priority | None = None
    assignees: list[str] = field(default_factory=list)
    include_closed: bool = False


def parse_list_input(text: str) -> ListInput:
    """Parse the argument text of /list: `mobile`, `#mobile !high @ali review all`."""
    result = ListInput()
    for word in text.split():
        token = _clean(word)
        lowered = normalize_apostrophes(token).lower()

        if match := _USERNAME_RE.match(token):
            result.assignees.append(match.group(1).lower())
        elif token.startswith("!") and (priority := _priority_for(token[1:])):
            result.priority = priority
        elif lowered in ALL_WORDS:
            result.include_closed = True
        elif lowered in STATUS_WORDS:
            result.statuses.add(STATUS_WORDS[lowered])
        elif match := _AREA_RE.match(token):
            result.area = match.group(1).lower()
        elif re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", token) and result.area is None:
            result.area = lowered
        else:
            raise InputError("bad_filter", word=word)
    return result
