"""Tool metadata queries (execution belongs to the runtime)."""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from forge.api.dependencies import SessionDependency
from forge.api.schemas import (
    ApprovalResponse,
    ArtifactResponse,
    ResolveApprovalRequest,
    ToolResponse,
)
from forge.application.approvals import list_approvals, list_artifacts, read_artifact
from forge.runtime.tools import ToolRegistry

router = APIRouter(tags=['tools'])


@router.get('/tools', response_model=list[ToolResponse])
def catalog():
    return ToolRegistry().catalog()


@router.get('/runs/{run_id}/approvals', response_model=list[ApprovalResponse])
def approvals(run_id: str, session: SessionDependency):
    return list_approvals(session, run_id)


@router.post('/approvals/{approval_id}/resolve', response_model=ApprovalResponse)
async def resolve(approval_id: str, body: ResolveApprovalRequest, request: Request):
    from forge.domain.runs import InvalidRunTransition
    try:
        return request.app.state.supervisor.resolve(approval_id, body.approved)
    except InvalidRunTransition:
        raise
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get('/runs/{run_id}/artifacts', response_model=list[ArtifactResponse])
def artifacts(run_id: str, session: SessionDependency):
    return list_artifacts(session, run_id)


@router.get('/runs/{run_id}/artifacts/{artifact_id}')
def download(run_id: str, artifact_id: str, session: SessionDependency, request: Request):
    artifact, data = read_artifact(session, run_id, artifact_id, request.app.state.settings.resolved_data_dir / 'workspaces')
    from urllib.parse import quote
    return Response(data, media_type=artifact.media_type,
                    headers={'Content-Disposition': "attachment; filename*=UTF-8''" + quote(Path(artifact.path).name, safe='')})
