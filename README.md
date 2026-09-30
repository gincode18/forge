# Forge

Local-first runtime and engineering platform for AI agents.

## Project layout

- `backend/` — FastAPI service and Forge's provider-neutral runtime.
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
(`Last-Event-ID` or `?since=N` replays events after sequence N). No-tool fake
and Gemini versions using the current finish-only `react` planner are runnable.
Set
`NEXT_PUBLIC_FORGE_API_URL` for the dashboard if the API is not at
`http://localhost:8000` (the URL must be reachable from both the browser and
the Next.js server; configure `FORGE_ALLOWED_ORIGINS` on the API for a different
dashboard origin).

### First real-provider slice (Phase 3)

To call Gemini, put `GEMINI_API_KEY=your-key` in **`backend/.env`**, or export
it into the API process environment. `backend/.env.example` is the safe template;
`.env` is ignored by Git. Start the API from `backend/` so settings load that
directory's `.env`; restart the API after editing it. Environment variables
override the file. Never put this key in Next.js, `NEXT_PUBLIC_*`, an agent
definition, or a request. The key is masked in settings representations.

Create an agent using
`provider: "gemini"`, `model: "gemini-3.5-flash-lite"`, a nonempty
`instructions` string and a name via `POST /api/v1/agents`; queue a run with
its `agent_id` via `POST /api/v1/runs`, then call
`POST /api/v1/runs/{run_id}/start`. Without the key, start returns 422 and
leaves the run queued. The model step persists normalized text, finish reason,
token usage, request ID, and latency. The default fake provider and test suite
remain offline and key-free. This is a no-tool single-turn completion, **not**
yet live token streaming or a multi-turn ReAct planner; Gemini creation is
currently API-only, not available from the dashboard form.

See [`docs/gemini-model-selection.md`](docs/gemini-model-selection.md) for the
dated cost comparison and a stronger Flash candidate. Model IDs are selected
per immutable agent version; existing versions are not changed by this advice.

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
