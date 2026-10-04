"""Opt-in content retention: retain execution identities and diagnostic metadata."""
import os
import stat
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from forge.adapters.sqlite.database import Database
from forge.adapters.sqlite.models import (
    ApprovalRecord,
    ArtifactRecord,
    EventRecord,
    RunCheckpointRecord,
    RunRecord,
    StepRecord,
)
from forge.adapters.sqlite.repositories import RunRepository
from forge.config import Settings
from forge.domain.runs import TERMINAL_RUN_STATUSES

EXPIRED = {'retained': False, 'reason': 'retention_expired'}
CONTENT_FIELDS = {'text', 'content', 'stdout', 'stderr', 'result', 'arguments', 'metadata', 'content_blocks',
                  'tool_calls', 'messages', 'instructions', 'input', 'response', 'output'}


def compact_content(value: dict) -> dict:
    """Discard content, keeping bounded timing, usage and diagnostic fields."""
    cleaned = {key: item for key, item in value.items() if key not in CONTENT_FIELDS}
    output = value.get('output')
    if isinstance(output, dict) and isinstance(output.get('error'), str):
        cleaned['output'] = {'error': output['error']}
    if cleaned != value:
        cleaned.update(EXPIRED)
    return cleaned


def remove_recorded_file(workspace: Path, value: str, *, dry_run: bool = False) -> None:
    """Descriptor-relative unlink; refuse traversal, symlinks and nonregular files.

    Missing files count as expired too, allowing retry after unlink/commit crashes.
    Like the runtime file tools, this is not protection from hostile host renames.
    """
    relative = Path(value)
    root = workspace.absolute()
    if relative.is_absolute() or '..' in relative.parts or not relative.parts or '..' in root.parts:
        raise ValueError('unsafe artifact path')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    with ExitStack() as stack:
        directory = os.open(root.anchor, flags)
        stack.callback(os.close, directory)
        for part in (*root.parts[1:], *relative.parts[:-1]):
            try:
                child = os.open(part, flags, dir_fd=directory)
            except FileNotFoundError:
                return
            stack.callback(os.close, child)
            directory = child
        try:
            info = os.stat(relative.name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            return
        if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1:
            raise ValueError('unsafe artifact file')
        if not dry_run:
            os.unlink(relative.name, dir_fd=directory)


def apply_retention(database: Database, settings: Settings, *, now: datetime | None = None, dry_run: bool = False) -> dict[str, int]:
    """Compact old terminal traces only; the default policy retains everything."""
    counts = {'events_compacted': 0, 'messages_compacted': 0, 'artifacts_expired': 0, 'artifact_errors': 0}
    compacted_events: set[str] = set()
    now = now or datetime.now(UTC)
    terminal = [status.value for status in TERMINAL_RUN_STATUSES]
    with Session(database.engine) as session:
        if settings.event_retention_days is not None:
            cutoff = now - timedelta(days=settings.event_retention_days)
            events = session.scalars(select(EventRecord).join(RunRecord).where(
                RunRecord.status.in_(terminal), RunRecord.updated_at < cutoff,
            ))
            for event in events:
                compacted = compact_content(event.payload)
                if compacted != event.payload:
                    counts['events_compacted'] += 1
                    compacted_events.add(event.id)
                    if not dry_run:
                        event.payload = compacted
        if settings.message_retention_days is not None:
            cutoff = now - timedelta(days=settings.message_retention_days)
            runs = list(session.scalars(select(RunRecord).where(
                RunRecord.status.in_(terminal), RunRecord.updated_at < cutoff,
            )))
            for run in runs:
                if run.input != '[expired by retention]':
                    counts['messages_compacted'] += 1
                    if not dry_run:
                        # Retention is not an execution transition; do not reset age.
                        session.execute(update(RunRecord).where(RunRecord.id == run.id).values(
                            input='[expired by retention]', updated_at=run.updated_at,
                        ))
                for step in session.scalars(select(StepRecord).where(StepRecord.run_id == run.id)):
                    if step.input != EXPIRED:
                        counts['messages_compacted'] += 1
                        if not dry_run:
                            step.input = dict(EXPIRED)
                    if step.output is not None:
                        compacted = compact_content(step.output)
                        if compacted != step.output:
                            counts['messages_compacted'] += 1
                            if not dry_run:
                                step.output = compacted
                for approval in session.scalars(select(ApprovalRecord).where(ApprovalRecord.run_id == run.id)):
                    if approval.arguments != EXPIRED and not dry_run:
                        approval.arguments = dict(EXPIRED)
                checkpoint = session.get(RunCheckpointRecord, run.id)
                if checkpoint is not None and not dry_run:
                    session.delete(checkpoint)
                # Model context may be duplicated in events as well as steps.
                for event in session.scalars(select(EventRecord).where(EventRecord.run_id == run.id)):
                    if event.id in compacted_events:
                        continue
                    compacted = compact_content(event.payload)
                    if compacted != event.payload:
                        counts['events_compacted'] += 1
                        if not dry_run:
                            event.payload = compacted
        if settings.artifact_retention_days is not None:
            cutoff = now - timedelta(days=settings.artifact_retention_days)
            artifacts = session.scalars(select(ArtifactRecord).join(RunRecord).where(
                RunRecord.status.in_(terminal), RunRecord.updated_at < cutoff,
            ))
            expired = {event.payload.get('id') for event in session.scalars(
                select(EventRecord).where(EventRecord.type == 'artifact.expired')
            )}
            for artifact in artifacts:
                if artifact.id in expired:
                    continue
                try:
                    remove_recorded_file(settings.resolved_data_dir / 'workspaces' / artifact.run_id, artifact.path, dry_run=dry_run)
                except (OSError, ValueError):
                    counts['artifact_errors'] += 1
                    continue
                counts['artifacts_expired'] += 1
                if not dry_run:
                    RunRepository(session).append_event(artifact.run_id, 'artifact.expired', {
                        'id': artifact.id, 'run_id': artifact.run_id,
                        'path': artifact.path, 'reason': 'retention_expired',
                    })
        if not dry_run:
            session.commit()
    return counts


def main() -> None:
    """Preview by default; --apply explicitly permits destructive content cleanup."""
    import argparse
    import json

    from forge.adapters.sqlite.database import run_migrations

    parser = argparse.ArgumentParser(description='Preview or apply configured terminal-run content retention.')
    parser.add_argument('--apply', action='store_true', help='Remove expired content and recorded artifact files')
    args = parser.parse_args()
    settings = Settings()
    settings.resolved_data_dir.mkdir(parents=True, exist_ok=True)
    run_migrations(settings.resolved_database_url)
    database = Database(settings.resolved_database_url)
    try:
        result = apply_retention(database, settings, dry_run=not args.apply)
        print(json.dumps({'dry_run': not args.apply, **result}))
    finally:
        database.close()


if __name__ == '__main__':
    main()
