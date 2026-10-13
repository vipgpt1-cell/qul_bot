from __future__ import annotations

import pytest

from qul_bot.domain.enums import Role
from qul_bot.domain.specialty import (
    SPECIALTY_ORDER,
    Specialty,
    from_code,
    is_clear_word,
    parse_specialty,
    to_code,
)
from qul_bot.errors import PermissionDenied
from qul_bot.services.workspaces import WorkspaceService
from tests.conftest import World


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("mobile", Specialty.MOBILE),
        ("MOBILE", Specialty.MOBILE),
        ("#backend", Specialty.BACKEND),
        ("front", Specialty.FRONTEND),
        ("pm", Specialty.PM),
        ("QA", Specialty.QA),
        ("devops", Specialty.DEVOPS),
        ("boshqa", Specialty.OTHER),
        ("designer", None),
        ("", None),
    ],
)
def test_parse_specialty(word: str, expected: Specialty | None) -> None:
    assert parse_specialty(word) is expected


def test_clear_words() -> None:
    for word in ("-", "none", "Yo'q", "yo‘q", "clear"):
        assert is_clear_word(word)
    assert not is_clear_word("backend")


def test_codes_round_trip() -> None:
    assert to_code(None) == 0
    assert from_code(0) is None
    assert from_code(99) is None
    for specialty in SPECIALTY_ORDER:
        assert from_code(to_code(specialty)) is specialty
    assert len({to_code(s) for s in SPECIALTY_ORDER}) == len(SPECIALTY_ORDER)


def test_the_requested_specialties_exist() -> None:
    assert {s.value for s in Specialty} == {
        "mobile", "frontend", "backend", "pm", "qa", "devops", "other",
    }  # fmt: skip


async def test_people_set_their_own_specialty(world: World) -> None:
    workspaces = WorkspaceService(world.session)
    membership = await workspaces.set_specialty(
        world.workspace.id, world.dev, Specialty.BACKEND, world.dev.id, Role.MEMBER
    )
    assert membership.specialty is Specialty.BACKEND
    cleared = await workspaces.set_specialty(
        world.workspace.id, world.dev, None, world.dev.id, Role.MEMBER
    )
    assert cleared.specialty is None


async def test_only_admins_set_other_peoples_specialty(world: World) -> None:
    workspaces = WorkspaceService(world.session)
    with pytest.raises(PermissionDenied):
        await workspaces.set_specialty(
            world.workspace.id, world.dev2, Specialty.QA, world.dev.id, Role.MEMBER
        )
    with pytest.raises(PermissionDenied):  # reviewers are not admins
        await workspaces.set_specialty(
            world.workspace.id, world.dev2, Specialty.QA, world.reviewer.id, Role.REVIEWER
        )
    done = await workspaces.set_specialty(
        world.workspace.id, world.dev2, Specialty.QA, world.admin.id, Role.ADMIN
    )
    assert done.specialty is Specialty.QA
