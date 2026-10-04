"""Nullable durable trace identities; historical events remain schema version one."""
import sqlalchemy as sa

from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

FIELDS = {'correlation_id': 36, 'causation_id': 36, 'trace_id': 32, 'span_id': 16}


def upgrade():
    for table in ('events', 'steps'):
        for name, length in FIELDS.items():
            op.add_column(table, sa.Column(name, sa.String(length), nullable=True))
    op.add_column('events', sa.Column('step_id', sa.String(36), nullable=True))


def downgrade():
    # A later 0004 refusal must not leave the live inspector missing its columns:
    # SQLite DDL is non-transactional, so preflight before dropping anything.
    blocked = op.get_bind().execute(sa.text(
        "SELECT EXISTS(SELECT 1 FROM runs WHERE status = 'waiting_for_approval') "
        "OR EXISTS(SELECT 1 FROM run_checkpoints) "
        "OR EXISTS(SELECT 1 FROM approvals WHERE status = 'pending')"
    )).scalar()
    if blocked:
        raise RuntimeError(
            'Cannot downgrade 0005 while approval waits or checkpoints exist; '
            'complete or cancel these runs and stop the runtime before retrying.'
        )
    # Native SQLite DROP COLUMN avoids rebuilding parent steps referenced by approvals.
    op.drop_column('events', 'step_id')
    for table in ('events', 'steps'):
        for name in reversed(FIELDS):
            op.drop_column(table, name)
