# Working on Forge

Forge is a **local-first runtime and engineering platform for AI agents**, not an
agent, chatbot, or provider wrapper. Its distinguishing feature is an inspectable
execution trace: a developer should be able to tell what ran, why, and where it
failed. Read `scope.md` for the vision, `architecture.md` for the current design,
and `plan.md` for the active phase and exit criteria. The architecture takes
precedence over the older stack/repository sketch in `scope.md`.

## Boundaries that matter

- The runtime owns execution. HTTP handlers translate requests; they do not
  perform model, planner, or tool work. The Next.js dashboard is an operator UI,
  never a second execution host or domain API.
- Keep a modular monolith. Pure `backend/src/forge/domain/` rules should not
  import FastAPI or SQLAlchemy. `runtime/` coordinates execution through
  interfaces, `application/` owns use cases, and `adapters/` persist or contact
  external systems. Add a boundary only when there is a real implementation.
- An `AgentVersion` is an immutable executable snapshot. Every run refers to
  one version; do not mutate historical configuration or delete its trace.
- Validate run transitions with the domain state machine. Persist run/step
  changes and typed, sequenced events together when possible. Events explain
  actions; normalized rows hold current state. A failed or interrupted run
  must remain diagnosable after restart.
- Do not hold a SQLite transaction across an async provider call. Treat SSE as
  delivery of **committed** events; reconnect/replay must not change the run.
- Keep the fake provider deterministic and the default suite offline/no-key.
  Implement core concepts in small vertical slices before introducing real
  providers, Redis, workers, containers, or plugin frameworks. Raspberry Pi
  deployment is the resource-conscious target.

## Repository map and checks

- `backend/src/forge/api/`, `application/`, `domain/`, `runtime/`,
  `adapters/sqlite/`: HTTP, use cases, invariants, orchestration, persistence.
- `backend/alembic/`: SQLite schema migrations. Test upgrade **and downgrade**
  when changing the schema; do not use `create_all` as a substitute.
- `backend/tests/unit/` and `integration/`: rules and real API/SQLite behavior.
  For behavior changes, write a failing test first, then implement and verify.
- `frontend/src/app/`, `components/`, `lib/`: Next.js App Router dashboard.
  Follow `frontend/AGENTS.md`: check the installed Next.js docs under
  `frontend/node_modules/next/dist/docs/` before changing framework patterns.
- `docs/decisions/`: record architectural choices and tradeoffs. Keep `plan.md`
  exit criteria honest; a partial slice is not a completed phase.

Run from the indicated directory before declaring work complete:

```text
backend/:  uv run pytest && uv run ruff check .
frontend/: pnpm lint && pnpm build     # when UI or API-facing types change
root/:     graphify update .           # after code changes
```

For a local smoke test, start the API with `cd backend && uv run fastapi dev
main.py` and the dashboard with `cd frontend && pnpm dev`. State defaults to
`backend/data/forge.db` and can be relocated with `FORGE_DATA_DIR` or
`FORGE_DATABASE_URL`. Never commit local data, credentials, or `.env` files.

## Navigating the graph

When the user types `/graphify`, load the installed graphify skill first. For
codebase questions, first run `graphify query "<question>"` when
`graphify-out/graph.json` exists; use `graphify path "<A>" "<B>"` for
relationships and `graphify explain "<concept>"` for one concept. If
`graphify-out/wiki/index.md` exists, use it for broad navigation. Read
`graphify-out/GRAPH_REPORT.md` only for broad architecture review or when a
scoped query is insufficient. Dirty graph files after hooks or incremental
updates are normal; skip the graph only when the graph itself is the problem
or the user explicitly opts out. After code edits, run `graphify update .`
(AST-only, no API cost).
