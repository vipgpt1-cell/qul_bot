from datetime import date

import pytest

from qul_bot.errors import InputError
from qul_bot.parsing.due import is_clear, parse_due

TODAY = date(2026, 10, 10)  # a Saturday


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("bugun", date(2026, 10, 10)),
        ("ertaga", date(2026, 10, 11)),
        ("Tomorrow", date(2026, 10, 11)),
        ("indinga", date(2026, 10, 12)),
        ("juma", date(2026, 10, 16)),
        ("dushanba", date(2026, 10, 12)),
        ("fri", date(2026, 10, 16)),
        ("shanba", date(2026, 10, 17)),  # today is Saturday: a bare weekday is the *next* one
        ("3d", date(2026, 10, 13)),
        ("+2w", date(2026, 10, 24)),
        ("25.10", date(2026, 10, 25)),
        ("25/10", date(2026, 10, 25)),
        ("25.10.2026", date(2026, 10, 25)),
        ("2026-11-01", date(2026, 11, 1)),
        ("05.10", date(2027, 10, 5)),  # already passed this year: next year
        ("29.02.2028", date(2028, 2, 29)),
    ],
)
def test_parse_due(text: str, expected: date) -> None:
    assert parse_due(text, TODAY) == expected


@pytest.mark.parametrize("text", ["", "   ", "soon", "32.01", "30.02.2027", "2026-13-01", "juma2"])
def test_invalid_due(text: str) -> None:
    with pytest.raises(InputError) as exc:
        parse_due(text, TODAY)
    assert exc.value.code == "invalid_due"


def test_past_date_is_rejected() -> None:
    with pytest.raises(InputError) as exc:
        parse_due("01.01.2026", TODAY)
    assert exc.value.code == "due_in_past"


@pytest.mark.parametrize("text", ["-", "none", "yoq", "Yo'q", "yo‘q"])
def test_clear_words(text: str) -> None:
    assert is_clear(text)
