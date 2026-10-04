"""Metadata-only JSON event logs emitted after the outer transaction commits."""
import json
import logging
import math
from datetime import UTC

from sqlalchemy import event

logger = logging.getLogger('forge.events')
_QUEUE = 'forge_committed_event_logs'
_HOOKS = 'forge_event_log_hooks'


def _after_commit(session):
    if session.in_nested_transaction():
        return
    for _, metadata in session.info.pop(_QUEUE, []):
        logger.info(json.dumps(metadata, separators=(',', ':'), allow_nan=False))


def _after_rollback(session):
    nested = session.get_nested_transaction()
    if nested is None:
        session.info.pop(_QUEUE, None)
    else:
        session.info[_QUEUE] = [
            (transaction, metadata)
            for transaction, metadata in session.info.get(_QUEUE, [])
            if not _within(transaction, nested)
        ]


def _within(transaction, ancestor):
    while transaction is not None:
        if transaction is ancestor:
            return True
        transaction = transaction.parent
    return False


def _after_transaction_end(session, transaction):
    if transaction.parent is None:
        # Closing an uncommitted session must also discard buffered metadata.
        session.info.pop(_QUEUE, None)


def queue_event_log(session, record, *, step=None, run=None):
    """Snapshot allowlisted fields while SQL access is still legal, not at commit."""
    # Embedded Alembic fileConfig disables existing application loggers at startup.
    # This dedicated event channel must remain active after migrations/restarts.
    logger.disabled = False
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.INFO)
    if not session.info.get(_HOOKS):
        event.listen(session, 'after_commit', _after_commit)
        event.listen(session, 'after_rollback', _after_rollback)
        event.listen(session, 'after_transaction_end', _after_transaction_end)
        session.info[_HOOKS] = True
    metadata = {
        'event_id': record.id,
        'event_type': record.type,
        'run_id': record.run_id,
        'step_id': record.step_id,
        'correlation_id': record.correlation_id,
        'causation_id': record.causation_id,
        'trace_id': record.trace_id,
        'span_id': record.span_id,
        'outcome': record.type.rsplit('.', 1)[-1],
    }
    duration = record.payload.get('duration_ms')
    if duration is None and step is not None and step.started_at and step.finished_at:
        duration = (step.finished_at.replace(tzinfo=UTC) - step.started_at.replace(tzinfo=UTC)).total_seconds() * 1000
    if duration is None and run is not None and record.type in {'run.completed', 'run.failed', 'run.cancelled'}:
        duration = (record.created_at.replace(tzinfo=UTC) - run.created_at.replace(tzinfo=UTC)).total_seconds() * 1000
    if isinstance(duration, (int, float)) and not isinstance(duration, bool) and math.isfinite(duration) and duration >= 0:
        metadata['duration_ms'] = duration
    transaction = session.get_nested_transaction() or session.get_transaction()
    session.info.setdefault(_QUEUE, []).append((transaction, metadata))
