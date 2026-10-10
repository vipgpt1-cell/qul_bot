from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from qul_bot.db.models import User


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_telegram(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str,
        last_name: str | None,
    ) -> User:
        """Find the user for a Telegram account, creating or refreshing it as needed."""
        user = await self._by_telegram_id(telegram_id)
        if user is None:
            try:
                async with self.session.begin_nested():
                    user = User(
                        telegram_id=telegram_id,
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    self.session.add(user)
            except IntegrityError:
                # Two first messages from the same person raced; the other one won.
                user = await self._by_telegram_id(telegram_id)
                assert user is not None
            return user

        if (user.username, user.first_name, user.last_name) != (username, first_name, last_name):
            user.username, user.first_name, user.last_name = username, first_name, last_name
        return user

    async def _by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()
