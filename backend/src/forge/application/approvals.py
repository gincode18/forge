"""Approval commands and artifact queries; short atomic storage transactions."""
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from forge.adapters.sqlite.models import ApprovalRecord, ArtifactRecord, utc_now
from forge.adapters.sqlite.repositories import RunRepository
from forge.application.errors import ResourceNotFoundError
from forge.application.runs import get_run
from forge.domain.runs import InvalidRunTransition, RunStatus
from forge.runtime.tools import open_scoped_file


def list_approvals(session, run_id):
    get_run(session, run_id)
    return list(session.scalars(select(ApprovalRecord).where(ApprovalRecord.run_id == run_id).order_by(ApprovalRecord.created_at)))


def resolve_approval(database, approval_id, approved):
    with Session(database.engine, expire_on_commit=False) as session:
        approval = session.get(ApprovalRecord, approval_id)
        if approval is None:
            raise ResourceNotFoundError('approval', approval_id)
        run = get_run(session, approval.run_id)
        if approval.status != 'pending' or run.status != RunStatus.WAITING_FOR_APPROVAL.value:
            raise InvalidRunTransition('approval is no longer pending')
        status = 'approved' if approved else 'rejected'
        result = session.execute(update(ApprovalRecord).where(ApprovalRecord.id == approval_id, ApprovalRecord.status == 'pending').values(status=status, resolved_at=utc_now()).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            raise InvalidRunTransition('approval was already resolved')
        runs = RunRepository(session)
        runs.append_event(run.id, 'approval.resolved', {'approval_id': approval_id, 'approved': approved})
        runs.transition(run, RunStatus.RUNNING, 'run.resumed')
        session.commit()
        session.refresh(approval)
        return approval


def list_artifacts(session, run_id):
    get_run(session, run_id)
    return list(session.scalars(select(ArtifactRecord).where(ArtifactRecord.run_id == run_id).order_by(ArtifactRecord.created_at)))


def read_artifact(session, run_id, artifact_id, root):
    get_run(session, run_id)
    artifact = session.get(ArtifactRecord, artifact_id)
    if artifact is None or artifact.run_id != run_id:
        raise ResourceNotFoundError('artifact', artifact_id)
    try:
        with open_scoped_file(root / run_id, artifact.path) as source:
            data = source.read(32769)
        if len(data) > 32768:
            raise ValueError('artifact too large')
    except (OSError, ValueError):
        raise ResourceNotFoundError('artifact', artifact_id) from None
    return artifact, data
