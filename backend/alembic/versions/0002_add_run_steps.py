"""Add durable, ordered run steps.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "steps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "sequence", name="uq_run_step_sequence"),
    )
    op.create_index("ix_steps_kind", "steps", ["kind"], unique=False)
    op.create_index("ix_steps_run_created", "steps", ["run_id", "created_at"])
    op.create_index("ix_steps_run_id", "steps", ["run_id"], unique=False)
    op.create_index("ix_steps_status", "steps", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_steps_status", table_name="steps")
    op.drop_index("ix_steps_run_id", table_name="steps")
    op.drop_index("ix_steps_run_created", table_name="steps")
    op.drop_index("ix_steps_kind", table_name="steps")
    op.drop_table("steps")
