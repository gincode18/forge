# Forge

Local-first runtime and engineering platform for AI agents.

## Project layout

- `backend/` — FastAPI service and future Forge runtime.
- `frontend/` — Next.js dashboard using Shadcn UI.

## Project documents

- [`scope.md`](scope.md) — vision and project philosophy.
- [`architecture.md`](architecture.md) — proposed UX and technical architecture.
- [`plan.md`](plan.md) — phased implementation roadmap and current position.

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

## Checks

```bash
cd backend && uv run pytest && uv run ruff check .
cd frontend && pnpm lint && pnpm build
```
