# Forge codebase guide

This guide explains what each part of Forge does and how the pieces will become
an agent harness. Read `scope.md` first for the purpose of the project and
`architecture.md` for the target design. This document stays close to the code
that exists today.

## What "agent harness" means

An agent harness is the controlled environment around an AI model. The model
can suggest a next action, but the harness owns execution. It loads the agent's
configuration, sends context to a model, interprets the response, checks tool
permissions, executes approved actions, records results, enforces limits, and
decides when the run is finished.

Forge separates three related records:

- **Run**: the whole request, such as "inspect my home lab".
- **Step**: one ordered operation inside the run, such as a model request or
  tool execution.
- **Event**: an append-only fact explaining what happened, such as
  `run.created` or `model.completed`.

Steps hold queryable current results. Events form the chronological audit
trail. Forge intentionally uses both instead of making the database fully
event-sourced.

## Request flow in the current code

Creating and executing a run follows this path:

```text
POST /api/v1/runs
  -> api/routes/runs.py          validates HTTP input and shapes output
  -> application/runs.py        performs the create-run use case
  -> sqlite/repositories.py     writes records through SQLAlchemy
  -> models.py                  maps Python records to SQLite tables
  -> runs + events tables       persist the run and run.created event
POST /api/v1/runs/{id}/start
  -> runtime/supervisor.py       atomically claims the run and owns the task
  -> runtime/engine.py           loads the immutable version; enforces limits
  -> runtime/fake.py             scripted model response and final decision
  -> sqlite/repositories.py     persists transitions, steps, and events
GET /api/v1/runs/{id}/stream
  -> routes/runs.py              replays committed events after a sequence
```

Reading steps follows the same direction:

```text
GET /api/v1/runs/{id}/steps
  -> API route
  -> application service verifies that the run exists
  -> repository selects steps ordered by sequence
  -> Pydantic schema serializes the response
```

The dependency direction matters: HTTP code may call application code, and
application code may use adapters. Domain code does not import FastAPI,
SQLAlchemy, or other infrastructure.

## Backend directories

### `domain/`

Pure Python concepts and rules. `agents.py` defines stable agent identities and
immutable executable versions. `runs.py` owns the run state machine. `steps.py`
defines the kinds and states of runtime operations. `events.py` defines the
shape of trace events.

This layer should be easy to test without a web server or database.

### `application/`

Use cases that coordinate work. For example, `create_run` verifies the selected
agent version, asks a repository to create the run, and commits the transaction.
This layer describes what Forge does without handling HTTP details.

### `adapters/sqlite/`

Infrastructure that makes the application durable. `models.py` contains the
SQLAlchemy table mappings, `repositories.py` contains database queries, and
`database.py` owns engines, sessions, and migration startup.

The domain `Step` and SQLAlchemy `StepRecord` look similar but have different
jobs: the first expresses the concept without infrastructure; the second knows
how that concept is stored.

### `api/`

The FastAPI boundary. `schemas.py` validates request and response data,
`routes/` maps URLs to application use cases, `dependencies.py` provides one
database session per request, and `app.py` assembles the service.

The API layer should translate, not contain planner or runtime behavior.

### `runtime/`

`ports.py` defines the normalized provider/planner contracts. `fake.py`
implements the no-key provider and finish-only planner; `gemini.py` adapts
the official Google Gen AI SDK. `engine.py` persists meaningful
boundaries, enforces step/time limits, and completes or fails a run.
`supervisor.py` owns in-process tasks, cancellation, and startup recovery.
It is not a distributed worker or durable mid-step resume engine.

### `alembic/`

Version-controlled database changes. Migration `0001` created agents, versions,
runs, and events. Migration `0002` adds ordered run steps. The API automatically
upgrades the local database on startup.

### `tests/`

Unit tests check isolated rules such as legal run-state transitions. Integration
tests exercise FastAPI, SQLite, migrations, persistence across restarts, and the
agent/run lifecycle.

## Frontend

`frontend/src/app/` is the Next.js dashboard. Agents can create and launch
fake runs; Runs lists persisted executions; `runs/[id]` streams the committed
event timeline via SSE and reloads status/steps. Disconnecting the page does
not cancel the supervisor task. The trace remains readable after completion.

## How the current runtime fits

The runtime sits between the API and either the fake or Gemini provider:

```text
supervisor claims and starts run
  -> runtime loads immutable AgentVersion
  -> planner prepares a model turn
  -> provider returns normalized text, usage, and metadata when available
  -> runtime creates/updates Step records
  -> runtime appends typed Event records
  -> run completes, fails, or is cancelled
```

The fake provider makes the harness testable without a key or network. The
`react` configuration name currently uses a finish-only planner, not tool
calling; Phase 3 has begun with Gemini single-turn completions, with the
multi-turn planner and streaming still outstanding.

## A useful reading order

1. `backend/src/forge/domain/runs.py` — understand the run state machine.
2. `backend/src/forge/domain/steps.py` — understand operations within a run.
3. `backend/src/forge/api/routes/runs.py` — see the HTTP boundary.
4. `backend/src/forge/application/runs.py` — see the use cases.
5. `backend/src/forge/adapters/sqlite/repositories.py` — see persistence logic.
6. `backend/src/forge/adapters/sqlite/models.py` — see the database mapping.
7. `backend/src/forge/runtime/engine.py` and `supervisor.py` — follow execution.
8. `backend/tests/integration/test_fake_runtime.py` — see executable examples.

## How to verify changes

From `backend/` run:

```bash
uv run pytest
uv run ruff check .
```

From `frontend/` run:

```bash
pnpm lint
pnpm build
```

When code changes, update the repository knowledge graph from the project root:

```bash
graphify update .
```
