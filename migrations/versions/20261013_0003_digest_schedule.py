"""automatic digest schedule per workspace

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.add_column(
            sa.Column("digest_enabled", sa.Boolean(), server_default=sa.true(), nullable=False)
        )
        batch_op.add_column(
            sa.Column("digest_time", sa.String(length=5), server_default="09:00", nullable=False)
        )
        batch_op.add_column(sa.Column("last_digest_on", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.drop_column("last_digest_on")
        batch_op.drop_column("digest_time")
        batch_op.drop_column("digest_enabled")
