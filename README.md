# Forge

Local-first runtime and engineering platform for AI agents.

## Project layout

- `backend/` — FastAPI service and Forge's first deterministic runtime.
- `frontend/` — Next.js dashboard using Shadcn UI.

## Project documents

- [`scope.md`](scope.md) — vision and project philosophy.
- [`architecture.md`](architecture.md) — proposed UX and technical architecture.
- [`plan.md`](plan.md) — phased implementation roadmap and current position.
- [`docs/codebase-guide.md`](docs/codebase-guide.md) — plain-English tour of the
  code and agent harness.
- [`docs/decisions/`](docs/decisions/) — architecture decisions and tradeoffs.

## Run locally

Start the API:

```bash
cd backend
uv run fastapi dev main.py
```

Start the dashboard in a second terminal:

```bash
cd frontend
pnpm dev
```

The API is available at `http://localhost:8000`, with interactive API docs at
`http://localhost:8000/docs`. The dashboard runs at `http://localhost:3000`.
Its status, Agents, and Runs pages read from the API. Create an agent, queue a
run from Agents, or queue one from Runs and select **Start fake run** on its
detail page. No model key is needed. The detail page streams persisted events
over SSE and shows the run status, steps, result, and cancellation controls.
The API accepts `POST /api/v1/runs/{run_id}/start` (202 on acceptance),
`POST /api/v1/runs/{run_id}/cancel`, and `GET /api/v1/runs/{run_id}/stream`
(`Last-Event-ID` or `?since=N` replays events after sequence N). Only
fake-provider, no-tool versions using the current `react` planner are runnable.
Set
`NEXT_PUBLIC_FORGE_API_URL` for the dashboard if the API is not at
`http://localhost:8000` (the URL must be reachable from both the browser and
the Next.js server; configure `FORGE_ALLOWED_ORIGINS` on the API for a different
dashboard origin).

Every API response includes a server-generated `X-Request-ID`. A newly queued
run's `run.created` event persists the creation request ID in its payload; the
event's `run_id` links it to the run. These IDs can be compared when debugging
requests, including after a restart.

Forge stores local state in `backend/data/forge.db` by default. Override the
directory with `FORGE_DATA_DIR` or provide a complete `FORGE_DATABASE_URL`.

Database migrations run automatically when the API starts. They can also be
managed explicitly from `backend/`:

```bash
uv run alembic upgrade head
uv run alembic downgrade -1
```

## Checks

```bash
cd backend && uv run pytest && uv run ruff check .
cd frontend && pnpm lint && pnpm build
```
