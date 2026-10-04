"""Run-scoped tool policy, durable pause, and execution boundaries."""
import asyncio
import json
import time
from dataclasses import asdict
from uuid import uuid4

from sqlalchemy.orm import Session

from forge.adapters.sqlite.models import (
    ApprovalRecord,
    ArtifactRecord,
    RunCheckpointRecord,
    StepRecord,
    utc_now,
)
from forge.adapters.sqlite.repositories import RunRepository
from forge.domain.runs import RunStatus
from forge.domain.steps import StepStatus
from forge.domain.tools import ToolExecutionError
from forge.observability.telemetry import boundary, safe_code
from forge.runtime.policy import ToolPolicy
from forge.runtime.ports import ModelMessage, ToolCall


def restore_messages(values):
    return tuple(ModelMessage(**{**v, 'tool_calls': tuple(ToolCall(**c) for c in v.get('tool_calls', []))}) for v in values)


async def execute_calls(database, run_id, calls, messages, enabled, registry, context,
                        max_steps, deadline, accounting, start_step, pending=None, *, claimed=False):
    for index, call in enumerate(calls):
        if asyncio.get_running_loop().time() >= deadline:
            with Session(database.engine) as session:
                runs = RunRepository(session)
                run = runs.get(run_id)
                if run.status == RunStatus.RUNNING.value:
                    if pending and index == 0:
                        step = session.get(StepRecord, pending['step_id'])
                        step.status = StepStatus.FAILED.value
                        step.error = {'type': 'TimeoutError', 'message': 'run deadline exhausted'}
                        step.finished_at = utc_now()
                        approval = session.get(ApprovalRecord, pending['approval_id'])
                        runs.append_event(run_id, 'tool.failed', {'step_id': step.id, 'tool_name': call.name, 'tool_version': approval.tool_version, 'call_id': call.id, 'output': {'error': 'timeout'}, 'duration_ms': 0})
                    runs.transition(run, RunStatus.FAILED, 'run.failed', {
                        'reason': 'timeout',
                        **({'step_id': pending['step_id']} if pending and index == 0 else {}),
                    })
                    session.commit()
            return None
        step_id = pending['step_id'] if pending and index == 0 else start_step(call)
        if step_id is None:
            return None
        # A durable approval reuses the step, not an ended SDK span. The initial
        # sensitive authorization segment has its own ID; resumed execution uses
        # the stable step span ID carried by tool.started/completed envelopes.
        selected = next((tool for key in enabled if (tool := registry.get(key)) is not None and tool.name == call.name), None)
        authorization = not (pending and index == 0) and selected is not None and selected.risk == 'sensitive'
        with boundary('tool.authorization' if authorization else 'tool', run_id, step_id,
                      span_key=f'{step_id}:authorization' if authorization else None) as operation:
            try:
                with boundary('policy', run_id, step_id, child=True) as policy_operation:
                    policy = ToolPolicy().evaluate(call, enabled, registry, context)
                    if asyncio.get_running_loop().time() >= deadline:
                        raise TimeoutError('run deadline exhausted')
                    policy_operation.outcome = policy.decision
            except asyncio.CancelledError:
                from forge.runtime.engine import _cancel_step

                _cancel_step(database, run_id, step_id, 'tool',
                             policy_operation.duration_ms, terminal=not claimed)
                raise
            except Exception as exc:
                from forge.runtime.engine import _fail_step

                _fail_step(database, run_id, step_id, 'tool', exc,
                           duration_ms=policy_operation.duration_ms)
                raise
            tool = policy.tool
            payload = {'step_id': step_id, 'tool_name': call.name,
                       'tool_version': tool.version if tool else '', 'call_id': call.id}
            decision, reason, arguments = policy.decision, policy.reason, policy.arguments
            if pending and index == 0:
                with Session(database.engine) as session:
                    approval = session.get(ApprovalRecord, pending['approval_id'])
                    if approval is None or approval.status not in ('approved', 'rejected'):
                        return None
                    if approval.status == 'rejected':
                        decision, reason = 'deny', 'approval_rejected'
                    elif decision != 'deny':
                        decision, reason = 'allow', 'approval_granted'
            else:
                with Session(database.engine) as session:
                    runs = RunRepository(session)
                    runs.append_event(run_id, 'tool.requested', {**payload, 'arguments': call.arguments})
                    runs.append_event(run_id, 'tool.policy', {**payload, 'decision': decision, 'reason': reason})
                    if decision == 'require_approval':
                        approval = ApprovalRecord(id=str(uuid4()), run_id=run_id, step_id=step_id,
                                                  tool_name=tool.name, tool_version=tool.version,
                                                  arguments=call.arguments, status='pending')
                        session.add(approval)
                        session.add(RunCheckpointRecord(run_id=run_id, payload={
                            'messages': [asdict(m) for m in messages],
                            'calls': [asdict(c) for c in calls[index:]],
                            'remaining_seconds': max(0, deadline - asyncio.get_running_loop().time()),
                            'accounting': accounting, 'step_id': step_id, 'approval_id': approval.id,
                        }))
                        runs.append_event(run_id, 'approval.requested', {**payload, 'approval_id': approval.id})
                        runs.transition(runs.get(run_id), RunStatus.WAITING_FOR_APPROVAL, 'run.paused')
                    session.commit()
                if decision == 'require_approval':
                    operation.outcome = 'paused'
                    return None
            started = time.monotonic()
            if decision == 'allow':
                with Session(database.engine) as session:
                    run = RunRepository(session).get(run_id)
                    if run.status != RunStatus.RUNNING.value:
                        return None
                    checkpoint = session.get(RunCheckpointRecord, run_id)
                    if checkpoint:
                        if checkpoint.payload.get('execution_started'):
                            return None
                        # Commit before invoking the tool: crash recovery must never
                        # replay an uncertain side effect, even if no output exists.
                        checkpoint.payload = {**checkpoint.payload, 'execution_started': True}
                    RunRepository(session).append_event(run_id, 'tool.started', payload)
                    session.commit()
            try:
                if decision == 'deny':
                    output = {'error': reason}
                    event = 'tool.denied'
                else:
                    async with asyncio.timeout_at(min(deadline, asyncio.get_running_loop().time() + tool.timeout_seconds)):
                        result = await tool.execute(arguments, context)
                        output = tool.output_model.model_validate(result).model_dump()
                        if len(json.dumps(output).encode()) > tool.max_output_bytes:
                            raise ToolExecutionError('output_limit')
                    event = 'tool.completed'
            except asyncio.CancelledError:
                from forge.runtime.engine import _cancel_step

                _cancel_step(database, run_id, step_id, 'tool',
                             (time.monotonic() - started) * 1000, terminal=not claimed)
                raise
            except Exception as error:  # noqa: BLE001 - tool exceptions are untrusted, never persist raw text.
                code = ('timeout' if isinstance(error, TimeoutError) else
                        safe_code(error) if isinstance(error, ToolExecutionError) else 'tool_execution_failed')
                output = {'error': code}
                event = 'tool.failed'
            operation.outcome = ('deny' if event == 'tool.denied' else
                                 'timeout' if output.get('error') == 'timeout' else
                                 'failed' if event == 'tool.failed' else 'completed')
            if event != 'tool.completed':
                operation.code = output['error']
            messages += (ModelMessage('tool', json.dumps(output), tool_name=call.name, call_id=call.id),)
            with Session(database.engine) as session:
                runs = RunRepository(session)
                run = runs.get(run_id)
                if run.status != RunStatus.RUNNING.value:
                    return None
                step = session.get(StepRecord, step_id)
                step.status = StepStatus.COMPLETED.value if event == 'tool.completed' else StepStatus.FAILED.value
                step.output = output
                if event != 'tool.completed':
                    step.error = {'type': 'ToolExecutionError', 'code': output['error'], 'message': output['error']}
                step.finished_at = utc_now()
                runs.append_event(run_id, event, {**payload, 'output': output, 'duration_ms': (time.monotonic() - started) * 1000})
                checkpoint = session.get(RunCheckpointRecord, run_id)
                if checkpoint:
                    session.delete(checkpoint)
                if event == 'tool.completed' and call.name == 'filesystem_write':
                    artifact = ArtifactRecord(id=str(uuid4()), run_id=run_id, path=output['path'],
                                              size_bytes=output['size_bytes'], media_type='text/plain', created_at=utc_now())
                    session.add(artifact)
                    runs.append_event(run_id, 'artifact.created', {k: getattr(artifact, k) for k in ('id', 'run_id', 'path', 'size_bytes', 'media_type')} | {'created_at': artifact.created_at.isoformat()})
                session.commit()
        pending = None
    return messages
