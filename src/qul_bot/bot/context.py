from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from qul_bot.db.models import Membership, User, Workspace
from qul_bot.domain.workflow import Actor
from qul_bot.errors import AppError
from qul_bot.i18n import Translator


@dataclass(slots=True)
class RequestContext:
    """Who is acting, in which workspace, resolved once per update by `ContextMiddleware`."""

    user: User
    workspace: Workspace | None
    membership: Membership | None
    tz: ZoneInfo
    t: Translator

    @property
    def today(self) -> date:
        return datetime.now(self.tz).date()

    def require_workspace(self) -> Workspace:
        if self.workspace is None:
            raise AppError("no_workspace")
        return self.workspace

    @property
    def actor(self) -> Actor:
        if self.membership is None:
            raise AppError("no_workspace")
        return Actor(user_id=self.user.id, role=self.membership.role)
