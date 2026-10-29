from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from string import Formatter

import pytest

from qul_bot.bot.commands import _MENU_ADMINS, _MENU_EVERYONE
from qul_bot.domain.enums import Priority, Role, TaskStatus
from qul_bot.domain.specialty import Specialty
from qul_bot.i18n import CATALOGS, DEFAULT_LOCALE, Translator
from qul_bot.i18n.uz import MESSAGES

SRC = Path(__file__).parents[1] / "src" / "qul_bot"
NAMESPACES = {
    "help", "chatid", "status", "priority", "role", "created", "edited", "restored", "card",
    "btn", "toast", "changed", "notify", "assigned", "unassigned", "comment", "delete", "list",
    "digest", "areas", "area", "team", "menu", "err", "picker", "specialty", "find", "history",
    "bug", "check", "release", "qa", "files", "kind",
}  # fmt: skip
TELEGRAM_TAGS = {"b", "i", "u", "s", "code", "pre", "a"}


def source_files() -> list[Path]:
    """Code that may reference message keys (not the catalog itself, not the schema)."""
    return [p for p in SRC.rglob("*.py") if p.name != "uz.py" and "db" not in p.parts]


def test_every_key_used_in_code_exists() -> None:
    used: set[str] = set()
    for path in source_files():
        for literal in re.findall(r"""["']([a-z]+(?:\.[a-z_]+)+)["']""", path.read_text()):
            if literal.split(".")[0] in NAMESPACES:
                used.add(literal)
    assert used, "scanner found nothing: the regex is broken"
    assert used - set(MESSAGES) == set()


def test_every_error_code_has_a_message() -> None:
    codes: set[str] = set()
    for path in source_files():
        text = path.read_text()
        codes |= set(
            re.findall(
                r'(?:InputError|NotFoundError|PermissionDenied|WorkflowError|AppError)\(\s*"(\w+)"',
                text,
            )
        )
    assert len(codes) > 20
    assert {f"err.{c}" for c in codes} - set(MESSAGES) == set()


def test_dynamic_key_families_are_complete() -> None:
    expected = {f"status.{s.value}" for s in TaskStatus}
    expected |= {f"changed.{s.value}" for s in TaskStatus} | {"changed.rejected"}
    expected |= {f"priority.{p.value}" for p in Priority}
    expected |= {f"role.{r.value}" for r in Role}
    expected |= {f"specialty.{s.value}" for s in Specialty} | {"specialty.none"}
    expected |= {f"menu.{name}" for name in (*_MENU_EVERYONE, *_MENU_ADMINS)}
    assert expected - set(MESSAGES) == set()


def test_no_unused_messages() -> None:
    text = "\n".join(p.read_text() for p in source_files())
    dynamic_prefixes = (
        "status.",
        "changed.",
        "priority.",
        "role.",
        "menu.",
        "err.",
        "specialty.",
        "help.page.",
        "help.btn.",
        "history.field.",
        "bug.field.",
        "bug.severity.",
    )
    unused = [
        key
        for key in MESSAGES
        if not key.startswith(dynamic_prefixes)
        and f'"{key}"' not in text
        and f"'{key}'" not in text
    ]
    assert unused == []


def test_menu_descriptions_fit_telegram_limits() -> None:
    for name in (*_MENU_EVERYONE, *_MENU_ADMINS):
        assert 3 <= len(MESSAGES[f"menu.{name}"]) <= 256


class _TagChecker(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.problems: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in TELEGRAM_TAGS:
            self.problems.append(f"unsupported tag <{tag}>")
        self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack.pop() != tag:
            self.problems.append(f"unbalanced </{tag}>")


@pytest.mark.parametrize("key", sorted(MESSAGES))
def test_message_is_valid_telegram_html(key: str) -> None:
    template = MESSAGES[key]
    list(Formatter().parse(template))  # raises on malformed placeholders
    checker = _TagChecker()
    # Fill placeholders with plain text so only the tags are judged.
    filled = re.sub(r"\{\w+\}", "x", template)
    checker.feed(filled)
    checker.close()
    assert checker.problems == []
    assert checker.stack == []


def test_translator_behaviour() -> None:
    t = Translator("uz")
    assert t("status.todo") == "Kutilmoqda"
    assert t("created.header") == MESSAGES["created.header"]
    assert t("no.such.key") == "no.such.key"
    # a missing parameter must not crash a handler; it stays visible instead
    assert "{number}" in t("err.task_not_found")
    assert "7" in t("err.task_not_found", number=7)
    assert Translator("xx").locale == DEFAULT_LOCALE


def test_all_locales_cover_the_default_locale() -> None:
    for locale, catalog in CATALOGS.items():
        assert set(MESSAGES) - set(catalog) == set(), f"{locale} is missing keys"
