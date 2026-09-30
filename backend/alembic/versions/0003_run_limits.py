"""Persist immutable per-version run limits.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_versions",
        sa.Column("timeout_seconds", sa.Float(), nullable=False, server_default="30"),
    )
    op.add_column(
        "agent_versions", sa.Column("max_tokens", sa.Integer(), nullable=True)
    )
    op.add_column(
        "agent_versions", sa.Column("max_cost_usd", sa.Float(), nullable=True)
    )
    op.add_column(
        "agent_versions",
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"),
    )
    op.add_column(
        "agent_versions",
        sa.Column(
            "max_output_tokens", sa.Integer(), nullable=False, server_default="2048"
        ),
    )
    op.add_column(
        "agent_versions", sa.Column("input_cost_per_million", sa.Float(), nullable=True)
    )
    op.add_column(
        "agent_versions",
        sa.Column("output_cost_per_million", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    with op.batch_alter_table("agent_versions") as batch:
        batch.drop_column("output_cost_per_million")
        batch.drop_column("input_cost_per_million")
        batch.drop_column("max_output_tokens")
        batch.drop_column("max_retries")
        batch.drop_column("max_cost_usd")
        batch.drop_column("max_tokens")
        batch.drop_column("timeout_seconds")
