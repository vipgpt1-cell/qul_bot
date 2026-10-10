"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-10 08:43:17.027950
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("telegram_id", name=op.f("uq_users_telegram_id")),
    )
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("task_counter", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspaces")),
        sa.UniqueConstraint("telegram_chat_id", name=op.f("uq_workspaces_telegram_chat_id")),
    )
    op.create_table(
        "areas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_areas_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_areas")),
        sa.UniqueConstraint("workspace_id", "slug", name=op.f("uq_areas_workspace_id_slug")),
    )
    op.create_index(op.f("ix_areas_workspace_id"), "areas", ["workspace_id"], unique=False)
    op.create_table(
        "memberships",
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_memberships_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_memberships_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("workspace_id", "user_id", name=op.f("pk_memberships")),
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("area_id", sa.Integer(), nullable=True),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("source_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["area_id"], ["areas.id"], name=op.f("fk_tasks_area_id_areas"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"], ["users.id"], name=op.f("fk_tasks_reporter_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_tasks_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
        sa.UniqueConstraint("workspace_id", "number", name=op.f("uq_tasks_workspace_id_number")),
    )
    op.create_index(
        "ix_tasks_workspace_id_status", "tasks", ["workspace_id", "status"], unique=False
    )
    op.create_table(
        "task_assignees",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name=op.f("fk_task_assignees_task_id_tasks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_task_assignees_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("task_id", "user_id", name=op.f("pk_task_assignees")),
    )
    op.create_index("ix_task_assignees_user_id", "task_assignees", ["user_id"], unique=False)
    op.create_table(
        "task_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_task_comments_author_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name=op.f("fk_task_comments_task_id_tasks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_comments")),
    )
    op.create_index(op.f("ix_task_comments_task_id"), "task_comments", ["task_id"], unique=False)
    op.create_table(
        "task_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_task_events_actor_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"], name=op.f("fk_task_events_task_id_tasks"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_task_events_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_events")),
    )
    op.create_index(op.f("ix_task_events_task_id"), "task_events", ["task_id"], unique=False)
    op.create_index(
        "ix_task_events_workspace_id_id", "task_events", ["workspace_id", "id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_task_events_workspace_id_id", table_name="task_events")
    op.drop_index(op.f("ix_task_events_task_id"), table_name="task_events")
    op.drop_table("task_events")
    op.drop_index(op.f("ix_task_comments_task_id"), table_name="task_comments")
    op.drop_table("task_comments")
    op.drop_index("ix_task_assignees_user_id", table_name="task_assignees")
    op.drop_table("task_assignees")
    op.drop_index("ix_tasks_workspace_id_status", table_name="tasks")
    op.drop_table("tasks")
    op.drop_table("memberships")
    op.drop_index(op.f("ix_areas_workspace_id"), table_name="areas")
    op.drop_table("areas")
    op.drop_table("workspaces")
    op.drop_table("users")
