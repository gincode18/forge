from datetime import UTC, datetime

import pytest

from forge.domain.runs import InvalidRunTransition, Run, RunStatus


def make_run(status: RunStatus = RunStatus.QUEUED) -> Run:
    now = datetime.now(UTC)
    return Run(
        id="run-1",
        agent_version_id="version-1",
        input="hello",
        status=status,
        created_at=now,
        updated_at=now,
    )


def test_queued_run_can_start() -> None:
    now = datetime.now(UTC)
    running = make_run().transition(RunStatus.RUNNING, at=now)

    assert running.status is RunStatus.RUNNING
    assert running.updated_at == now


def test_terminal_run_cannot_transition() -> None:
    with pytest.raises(InvalidRunTransition, match="cannot transition"):
        make_run(RunStatus.COMPLETED).transition(
            RunStatus.RUNNING,
            at=datetime.now(UTC),
        )
