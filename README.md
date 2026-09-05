# Forge

Local-first runtime and engineering platform for AI agents.

## Project layout

- `backend/` — FastAPI service and future Forge runtime.
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
