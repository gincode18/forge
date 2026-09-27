# 0003 — In-process supervision for deterministic runs

## Context

Forge needs a first runnable vertical slice before adding external model calls, workers, or a broker. Runs, agent versions, steps, and ordered events already live in SQLite. HTTP requests should not own execution tasks.

## Decision

A FastAPI-lifespan `RunSupervisor` atomically claims a no-tool fake-provider run in SQLite, schedules it as an asyncio task, and returns HTTP 202. It rejects unsupported versions and duplicate starts. The runtime loads the immutable version, executes a scripted fake provider and finish-only planner, and commits step and event boundaries around the provider and planner operations. No database transaction stays open during the provider call. The supervisor can cancel queued/running work, and the runtime enforces a step cap and a wall-clock deadline. Startup converts abandoned running records and steps to `interrupted`; shutdown cancels owned tasks and then performs the same recovery. The detail UI follows committed events via SSE, with replay by sequence number and fresh status/step reads. A browser disconnect does not own or cancel execution.

## Alternatives

- Execute during the HTTP request: simple, but disconnects and request timeouts would own task lifetime.
- Add a durable queue and separate worker: stronger scheduling, but extra infrastructure before the runtime semantics are established.
- Treat events as the whole source of truth: unnecessary while normalized tables already track current state.

## Consequences

This is single-process, best-effort scheduling: atomic claiming avoids duplicate execution, but an API process crash after claim and before task scheduling is recovered as interrupted, not resumed. Events are replayed from SQLite; the SSE endpoint currently polls for committed rows, not an in-memory event bus. Synchronous planner work cannot be preempted mid-call, but an overrun is recorded on return. Storage protocols are deferred until a second adapter warrants them. The planner name `react` is accepted for now, but this slice's planner only finishes; it is not a ReAct tool loop. This resembles an in-memory worker supervised by an API process, not a durable workflow engine such as Temporal or LangGraph's checkpointing runtime.
