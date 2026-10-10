from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import DateTime, Dialect, Enum
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware UTC datetimes on every backend (SQLite drops tzinfo on its own)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime passed to a UTCDateTime column")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def str_enum(enum_cls: type[PyEnum], length: int) -> Enum:
    """Store an enum as plain VARCHAR holding its *value*.

    No native database enum type, so adding a status later is a code change, not a migration.
    """
    return Enum(
        enum_cls,
        native_enum=False,
        length=length,
        create_constraint=False,
        values_callable=lambda members: [member.value for member in members],
    )


def json_default() -> dict[str, Any]:
    return {}
