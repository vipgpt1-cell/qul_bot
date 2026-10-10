"""Keeps the places that must agree about command names in agreement."""

from __future__ import annotations

from qul_bot.bot.commands import (
    _MENU_ADMINS,
    _MENU_EVERYONE,
    ADMIN_COMMANDS,
    ALL_COMMANDS,
    EDIT_COMMANDS,
    LIST_COMMANDS,
    PUBLIC_COMMANDS,
    STATUS_COMMANDS,
    TASK_COMMANDS,
)
from qul_bot.domain.areas import RESERVED_SLUGS


def test_every_command_name_is_reserved_so_no_area_can_shadow_it() -> None:
    assert set(ALL_COMMANDS) - RESERVED_SLUGS == set()


def test_command_names_are_valid_for_telegram() -> None:
    for name in ALL_COMMANDS:
        assert name.islower()
        assert name.replace("_", "").isalnum()
        assert 1 <= len(name) <= 32


def test_no_duplicate_commands() -> None:
    assert len(ALL_COMMANDS) == len(set(ALL_COMMANDS))


def test_menus_only_list_real_commands() -> None:
    assert set(_MENU_EVERYONE) | set(_MENU_ADMINS) <= set(ALL_COMMANDS)


def test_groups_cover_everything() -> None:
    grouped = {
        *PUBLIC_COMMANDS,
        *TASK_COMMANDS,
        *LIST_COMMANDS,
        *EDIT_COMMANDS,
        *STATUS_COMMANDS,
        "done",
        *ADMIN_COMMANDS,
    }
    assert grouped == set(ALL_COMMANDS)
