from __future__ import annotations

import re
from collections.abc import Sequence

from aiogram.types import Message, ReplyParameters
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.bot.context import RequestContext
from qul_bot.db.models import User
from qul_bot.domain.enums import Role
from qul_bot.errors import InputError, NotFoundError, PermissionDenied
from qul_bot.services.users import UserService
from qul_bot.services.workspaces import WorkspaceService

_TASK_REF_RE = re.compile(r"^\s*#?(\d{1,9})(?:\s+(.*))?$", re.DOTALL)


def parse_ref(args: str | None) -> tuple[int, str]:
    """Split `42 some text` / `#42 some text` into the task number and the rest."""
    match = _TASK_REF_RE.match(args or "")
    if not match:
        raise InputError("task_ref_required")
    return int(match.group(1)), (match.group(2) or "").strip()


def reply_to(message_id: int | None) -> ReplyParameters | None:
    if message_id is None:
        return None
    return ReplyParameters(message_id=message_id, allow_sending_without_reply=True)


async def member_from_telegram(
    session: AsyncSession, ctx: RequestContext, tg_user: TelegramUser
) -> User:
    """Turn someone we only saw in a reply into a known workspace member."""
    workspace = ctx.require_workspace()
    user = await UserService(session).upsert_telegram(
        tg_user.id, tg_user.username, tg_user.first_name, tg_user.last_name
    )
    workspaces = WorkspaceService(session)
    if await workspaces.get_membership(workspace.id, user.id) is None:
        await workspaces.add_member(workspace.id, user, Role.MEMBER)
    return user


async def replied_user(session: AsyncSession, ctx: RequestContext, message: Message) -> User | None:
    """The author of the message this command replies to (ignoring bots), if any."""
    source = message.reply_to_message
    if source is None or source.from_user is None or source.from_user.is_bot:
        return None
    return await member_from_telegram(session, ctx, source.from_user)


async def resolve_usernames(
    session: AsyncSession, ctx: RequestContext, usernames: Sequence[str]
) -> list[User]:
    workspace = ctx.require_workspace()
    workspaces = WorkspaceService(session)
    users: list[User] = []
    for username in usernames:
        user = await workspaces.find_member_by_username(workspace.id, username)
        if user is None:
            raise NotFoundError("unknown_user", username=username)
        users.append(user)
    return users


def require_admin(ctx: RequestContext) -> None:
    if ctx.membership is None or ctx.membership.role is not Role.ADMIN:
        raise PermissionDenied("admin_required")
