from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from qul_bot.db.models import Workspace
from qul_bot.domain.schedule import is_digest_due, parse_clock


class DigestService:
    """Decides which workspaces are due for their automatic daily digest."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def claim_due(self, now: datetime) -> list[Workspace]:
        """Workspaces whose digest is due at `now`, each marked as posted for today.

        The mark is written *before* anything is sent, so a crash or a failed send means a
        missed digest rather than a duplicate: at most once per workspace per day.
        """
        if now.tzinfo is None:
            raise ValueError("`now` must be timezone-aware")
        result = await self.session.execute(
            select(Workspace).where(
                Workspace.digest_enabled.is_(True), Workspace.telegram_chat_id.is_not(None)
            )
        )
        due: list[Workspace] = []
        for workspace in result.scalars().all():
            local_now = now.astimezone(ZoneInfo(workspace.timezone))
            if is_digest_due(
                enabled=workspace.digest_enabled,
                local_now=local_now,
                at=parse_clock(workspace.digest_time),
                last_sent_on=workspace.last_digest_on,
            ) and await self._claim(workspace.id, local_now.date()):
                # The UPDATE bypassed the ORM; keep the loaded object in step with the row.
                set_committed_value(workspace, "last_digest_on", local_now.date())
                due.append(workspace)
        return due

    async def _claim(self, workspace_id: int, local_date: date) -> bool:
        """Atomic compare-and-set: only one caller can claim a given day."""
        outcome = await self.session.execute(
            update(Workspace)
            .where(
                Workspace.id == workspace_id,
                or_(Workspace.last_digest_on.is_(None), Workspace.last_digest_on < local_date),
            )
            .values(last_digest_on=local_date)
            .execution_options(synchronize_session=False)
        )
        return bool(outcome.rowcount == 1)  # type: ignore[attr-defined]
