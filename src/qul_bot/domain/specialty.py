"""A person's specialty: which part of the team they belong to.

Not to be confused with *areas* (`#mobile`), which label parts of the *product*. A specialty
describes the *person*, and lets a task giver pick an assignee from the right group.
"""

from __future__ import annotations

from enum import StrEnum


class Specialty(StrEnum):
    MOBILE = "mobile"
    FRONTEND = "frontend"
    BACKEND = "backend"
    PM = "pm"
    QA = "qa"
    DEVOPS = "devops"
    OTHER = "other"


#: Display order. The position (+1) is also what inline-button callback data carries.
SPECIALTY_ORDER: tuple[Specialty, ...] = tuple(Specialty)

_ALIASES: dict[str, Specialty] = {
    "mobile": Specialty.MOBILE,
    "mob": Specialty.MOBILE,
    "frontend": Specialty.FRONTEND,
    "front": Specialty.FRONTEND,
    "backend": Specialty.BACKEND,
    "back": Specialty.BACKEND,
    "pm": Specialty.PM,
    "qa": Specialty.QA,
    "test": Specialty.QA,
    "tester": Specialty.QA,
    "devops": Specialty.DEVOPS,
    "ops": Specialty.DEVOPS,
    "other": Specialty.OTHER,
    "boshqa": Specialty.OTHER,
}

#: Words that clear a specialty.
CLEAR_WORDS = frozenset({"-", "none", "clear", "yoq", "yo'q"})


def parse_specialty(word: str) -> Specialty | None:
    """The specialty a word names, or None if it names none."""
    return _ALIASES.get(word.strip().lower().lstrip("#"))


def is_clear_word(word: str) -> bool:
    return word.strip().lower().replace("‘", "'").replace("’", "'") in CLEAR_WORDS


def to_code(specialty: Specialty | None) -> int:
    """Compact form for callback data: 0 = no specialty, 1.. = position in SPECIALTY_ORDER."""
    return 0 if specialty is None else SPECIALTY_ORDER.index(specialty) + 1


def from_code(code: int) -> Specialty | None:
    return SPECIALTY_ORDER[code - 1] if 0 < code <= len(SPECIALTY_ORDER) else None
