"""Database schema.

Design notes
------------
* `Workspace` is the unit of tenancy. Today one Telegram group is one workspace; the chat id is
  nullable and unique so web- or Slack-created workspaces can exist later.
* `User` is our own identity. The Telegram id is just one way to reach it, so a future task
  system can attach other identities without touching tasks.
* `TaskEvent` is an append-only log of everything that happens to a task. It gives history
  today and is the feed integrations (GitHub, own platform) will consume later.
* Tasks are soft-deleted; their number is never reused.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from qul_bot.db.base import Base
from qul_bot.db.types import UTCDateTime, json_default, str_enum, utcnow
from qul_bot.domain.enums import EventType, Priority, Role, TaskKind, TaskStatus
from qul_bot.domain.specialty import Specialty


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    locale: Mapped[str] = mapped_column(String(8), default="uz")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Tashkent")
    #: Last issued task number; bumped atomically so numbers are gap-free and race-free.
    task_counter: Mapped[int] = mapped_column(default=0)
    #: Automatic daily digest: on/off, local time "HH:MM", and the last local date it was posted.
    digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    digest_time: Mapped[str] = mapped_column(String(5), default="09:00", server_default="09:00")
    last_digest_on: Mapped[date | None] = mapped_column(Date)
    #: Use the QA (testing) step when the team has at least one QA.
    qa_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str] = mapped_column(String(255), default="")
    last_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    @property
    def display_name(self) -> str:
        full = f"{self.first_name} {self.last_name or ''}".strip()
        return full or self.username or f"user{self.id}"


class Membership(Base):
    __tablename__ = "memberships"

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[Role] = mapped_column(str_enum(Role, 16), default=Role.MEMBER)
    #: Which part of the team the person belongs to (mobile, backend, ...); optional.
    specialty: Mapped[Specialty | None] = mapped_column(str_enum(Specialty, 16))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    user: Mapped[User] = relationship(lazy="joined")


class Area(Base):
    __tablename__ = "areas"
    __table_args__ = (UniqueConstraint("workspace_id", "slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


task_assignees = Table(
    "task_assignees",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_task_assignees_user_id", "user_id"),
)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("workspace_id", "number"),
        Index("ix_tasks_workspace_id_status", "workspace_id", "status"),
        Index("ix_tasks_workspace_id_release", "workspace_id", "release"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    #: The short, human-facing id (`#42`), unique per workspace.
    number: Mapped[int]
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(str_enum(TaskStatus, 16), default=TaskStatus.TODO)
    priority: Mapped[Priority] = mapped_column(str_enum(Priority, 16), default=Priority.NORMAL)
    kind: Mapped[TaskKind] = mapped_column(
        str_enum(TaskKind, 8), default=TaskKind.TASK, server_default=TaskKind.TASK.value
    )
    #: The release (version) this task ships in, e.g. "1.4.0".
    release: Mapped[str | None] = mapped_column(String(32))
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id", ondelete="SET NULL"))
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    due_date: Mapped[date | None] = mapped_column(Date)
    #: The chat message this task was created from (for "go to message" links).
    source_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    source_message_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    area: Mapped[Area | None] = relationship(lazy="selectin")
    reporter: Mapped[User] = relationship(lazy="selectin")
    assignees: Mapped[list[User]] = relationship(
        secondary=task_assignees, lazy="selectin", order_by=User.id
    )


class ChecklistItem(Base):
    """One line of a task's test checklist; all must be ticked before the task is done."""

    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    text: Mapped[str] = mapped_column(String(200))
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    done_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    done_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class TaskAttachment(Base):
    """A file kept on Telegram's servers and referenced by its file id (e.g. a bug screenshot)."""

    __tablename__ = "task_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # "photo" | "document"
    file_id: Mapped[str] = mapped_column(String(255))
    caption: Mapped[str | None] = mapped_column(Text)
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class TaskComment(Base):
    __tablename__ = "task_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    author: Mapped[User] = relationship(lazy="selectin")


class TaskEvent(Base):
    __tablename__ = "task_events"
    __table_args__ = (Index("ix_task_events_workspace_id_id", "workspace_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    type: Mapped[EventType] = mapped_column(str_enum(EventType, 32))
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=json_default)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    actor: Mapped[User | None] = relationship(lazy="selectin")
