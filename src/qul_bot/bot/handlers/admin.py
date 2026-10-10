"""Workspace administration: areas, team roles."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.bot.context import RequestContext
from qul_bot.bot.formatting import esc, user_name
from qul_bot.bot.handlers.helpers import replied_user, require_admin, resolve_usernames
from qul_bot.domain.enums import Role
from qul_bot.errors import InputError
from qul_bot.parsing.task_input import normalize_apostrophes
from qul_bot.services.workspaces import WorkspaceService

_ROLE_WORDS: dict[str, Role] = {
    "admin": Role.ADMIN,
    "reviewer": Role.REVIEWER,
    "tekshiruvchi": Role.REVIEWER,
    "member": Role.MEMBER,
    "azo": Role.MEMBER,
    "a'zo": Role.MEMBER,
}
_ROLE_ICONS = {Role.ADMIN: "👑", Role.REVIEWER: "🔍", Role.MEMBER: "👤"}


async def cmd_areas(message: Message, session: AsyncSession, ctx: RequestContext) -> None:
    workspace = ctx.require_workspace()
    areas = await WorkspaceService(session).list_areas(workspace.id)
    if not areas:
        await message.answer(ctx.t("areas.empty"))
        return
    lines = [ctx.t("areas.title"), ""]
    lines += [f"/{esc(area.slug)} — {esc(area.name)} ({count})" for area, count in areas]
    lines += ["", ctx.t("areas.hint")]
    await message.answer("\n".join(lines))


async def cmd_add_area(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    require_admin(ctx)
    workspace = ctx.require_workspace()
    parts = (command.args or "").split(maxsplit=1)
    if not parts:
        raise InputError("addarea_usage")
    area = await WorkspaceService(session).add_area(
        workspace.id, parts[0], parts[1] if len(parts) > 1 else None
    )
    await message.answer(ctx.t("area.added", slug=esc(area.slug), name=esc(area.name)))


async def cmd_del_area(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    require_admin(ctx)
    workspace = ctx.require_workspace()
    if not (command.args or "").strip():
        raise InputError("delarea_usage")
    area = await WorkspaceService(session).remove_area(workspace.id, command.args or "")
    await message.answer(ctx.t("area.removed", slug=esc(area.slug)))


async def cmd_team(message: Message, session: AsyncSession, ctx: RequestContext) -> None:
    workspace = ctx.require_workspace()
    members = await WorkspaceService(session).list_members(workspace.id)
    lines = [ctx.t("team.title"), ""]
    for member in members:
        role = ctx.t(f"role.{member.role.value}")
        lines.append(f"{_ROLE_ICONS[member.role]} {user_name(member.user)} — {role}")
    lines += ["", ctx.t("team.hint")]
    await message.answer("\n".join(lines))


async def cmd_role(
    message: Message, command: CommandObject, session: AsyncSession, ctx: RequestContext
) -> None:
    """`/role @user reviewer`, or reply to a person's message with `/role reviewer`."""
    require_admin(ctx)
    workspace = ctx.require_workspace()
    role: Role | None = None
    usernames: list[str] = []
    for word in (command.args or "").split():
        if word.startswith("@"):
            usernames.append(word.lstrip("@").lower())
        else:
            role = _ROLE_WORDS.get(normalize_apostrophes(word).lower(), role)
    if role is None:
        raise InputError("role_usage")

    users = await resolve_usernames(session, ctx, usernames)
    if replied := await replied_user(session, ctx, message):
        users.append(replied)
    if not users:
        raise InputError("role_usage")

    workspaces = WorkspaceService(session)
    for user in users:
        await workspaces.set_role(workspace.id, user, role)
    await message.answer(
        ctx.t(
            "role.changed",
            users=", ".join(user_name(u) for u in users),
            role=ctx.t(f"role.{role.value}"),
        )
    )


def register(router: Router) -> None:
    router.message.register(cmd_areas, Command("areas", ignore_case=True))
    router.message.register(cmd_add_area, Command("addarea", ignore_case=True))
    router.message.register(cmd_del_area, Command("delarea", ignore_case=True))
    router.message.register(cmd_team, Command("team", ignore_case=True))
    router.message.register(cmd_role, Command("role", ignore_case=True))
