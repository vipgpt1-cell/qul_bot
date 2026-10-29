"""qa step, bug reports, releases, checklists, attachments

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "checklist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=200), nullable=False),
        sa.Column("done", sa.Boolean(), nullable=False),
        sa.Column("done_by_id", sa.Integer(), nullable=True),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["done_by_id"], ["users.id"], name=op.f("fk_checklist_items_done_by_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name=op.f("fk_checklist_items_task_id_tasks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_checklist_items")),
    )
    op.create_index(op.f("ix_checklist_items_task_id"), "checklist_items", ["task_id"])

    op.create_table(
        "task_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("file_id", sa.String(length=255), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("uploader_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name=op.f("fk_task_attachments_task_id_tasks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploader_id"], ["users.id"], name=op.f("fk_task_attachments_uploader_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_attachments")),
    )
    op.create_index(op.f("ix_task_attachments_task_id"), "task_attachments", ["task_id"])

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(
            sa.Column("kind", sa.String(length=8), server_default="task", nullable=False)
        )
        batch_op.add_column(sa.Column("release", sa.String(length=32), nullable=True))
        batch_op.create_index("ix_tasks_workspace_id_release", ["workspace_id", "release"])

    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.add_column(
            sa.Column("qa_enabled", sa.Boolean(), server_default=sa.true(), nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.drop_column("qa_enabled")
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("ix_tasks_workspace_id_release")
        batch_op.drop_column("release")
        batch_op.drop_column("kind")
    op.drop_index(op.f("ix_task_attachments_task_id"), table_name="task_attachments")
    op.drop_table("task_attachments")
    op.drop_index(op.f("ix_checklist_items_task_id"), table_name="checklist_items")
    op.drop_table("checklist_items")
