"""Durable approval checkpoint and workspace artifact metadata."""
import sqlalchemy as sa

from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('run_checkpoints',
        sa.Column('run_id', sa.String(36), sa.ForeignKey('runs.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('payload', sa.JSON(), nullable=False))
    op.create_table('approvals',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_id', sa.String(36), sa.ForeignKey('steps.id'), nullable=False),
        sa.Column('tool_name', sa.String(80), nullable=False),
        sa.Column('tool_version', sa.String(80), nullable=False),
        sa.Column('arguments', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True)))
    op.create_table('artifacts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('media_type', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))


def downgrade():
    # SQLite DDL is non-transactional: refuse before dropping any diagnostic state.
    connection = op.get_bind()
    blocked = connection.execute(sa.text(
        "SELECT EXISTS(SELECT 1 FROM runs WHERE status = 'waiting_for_approval') "
        "OR EXISTS(SELECT 1 FROM run_checkpoints) "
        "OR EXISTS(SELECT 1 FROM approvals WHERE status = 'pending')"
    )).scalar()
    if blocked:
        raise RuntimeError(
            'Cannot downgrade 0004 while approval waits or checkpoints exist; '
            'complete or cancel these runs and stop the runtime before retrying.'
        )
    op.drop_table('artifacts')
    op.drop_table('approvals')
    op.drop_table('run_checkpoints')
