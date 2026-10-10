from datetime import date

import pytest

from qul_bot.domain.enums import Priority, TaskStatus
from qul_bot.errors import InputError
from qul_bot.parsing.task_input import parse_list_input, parse_task_input

TODAY = date(2026, 10, 10)


def test_plain_title() -> None:
    parsed = parse_task_input("Fix the login crash", TODAY)
    assert parsed.title == "Fix the login crash"
    assert parsed.area is None
    assert parsed.priority is None
    assert parsed.assignees == []
    assert parsed.due is None


def test_all_tokens_in_any_position() -> None:
    parsed = parse_task_input(
        "#mobile Fix login @alisher1 crash !yuqori muddat:ertaga @valijon1", TODAY
    )
    assert parsed.title == "Fix login crash"
    assert parsed.area == "mobile"
    assert parsed.priority is Priority.HIGH
    assert parsed.assignees == ["alisher1", "valijon1"]
    assert parsed.due == date(2026, 10, 11)


def test_trailing_comma_does_not_break_mentions() -> None:
    assert parse_task_input("Fix @alisher1, @valijon1; now", TODAY).assignees == [
        "alisher1",
        "valijon1",
    ]


def test_mentions_are_lowercased_and_deduplicated() -> None:
    assert parse_task_input("x @Alisher1 @alisher1", TODAY).assignees == ["alisher1"]


@pytest.mark.parametrize(
    ("word", "priority"),
    [
        ("!urgent", Priority.URGENT),
        ("!shoshilinch", Priority.URGENT),
        ("!HIGH", Priority.HIGH),
        ("!o'rta", Priority.NORMAL),
        ("!o‘rta", Priority.NORMAL),
        ("!past", Priority.LOW),
        ("!p0", Priority.URGENT),
    ],
)
def test_priority_words(word: str, priority: Priority) -> None:
    assert parse_task_input(f"Title {word}", TODAY).priority is priority


def test_unknown_bang_word_stays_in_title() -> None:
    assert parse_task_input("Fix this !important thing!", TODAY).title == (
        "Fix this !important thing!"
    )


def test_hash_number_is_not_an_area() -> None:
    assert parse_task_input("Related to #42", TODAY).title == "Related to #42"


def test_due_aliases() -> None:
    for key in ("due", "muddat", "deadline", "MUDDAT"):
        assert parse_task_input(f"x {key}:3d", TODAY).due == date(2026, 10, 13)


def test_invalid_due_raises() -> None:
    with pytest.raises(InputError):
        parse_task_input("x muddat:someday", TODAY)


def test_clearing_tokens_for_edit() -> None:
    parsed = parse_task_input("#- muddat:-", TODAY)
    assert parsed.clear_area
    assert parsed.clear_due
    assert parsed.title == ""


def test_multiline_becomes_title_and_description() -> None:
    parsed = parse_task_input("Crash on start #mobile\nSteps:\n1. open app", TODAY)
    assert parsed.title == "Crash on start"
    assert parsed.description == "Steps:\n1. open app"


def test_title_too_long() -> None:
    with pytest.raises(InputError) as exc:
        parse_task_input("x" * 201, TODAY)
    assert exc.value.code == "title_too_long"


def test_empty_input() -> None:
    parsed = parse_task_input("   ", TODAY)
    assert parsed.title == ""


def test_list_filters() -> None:
    parsed = parse_list_input("mobile !high @alisher1 review all")
    assert parsed.area == "mobile"
    assert parsed.priority is Priority.HIGH
    assert parsed.assignees == ["alisher1"]
    assert parsed.statuses == {TaskStatus.REVIEW}
    assert parsed.include_closed


def test_list_filters_uzbek_and_hash() -> None:
    parsed = parse_list_input("#backend tekshiruvda")
    assert parsed.area == "backend"
    assert parsed.statuses == {TaskStatus.REVIEW}


def test_list_filters_reject_garbage() -> None:
    with pytest.raises(InputError):
        parse_list_input("mobile $$$")
