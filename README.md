# Forge

Local-first runtime and engineering platform for AI agents.

## Project layout

- `backend/` — FastAPI service and future Forge runtime.
- `frontend/` — Next.js dashboard using Shadcn UI.

## Run locally

Start the API:

```bash
cd backend
uv run fastapi dev main.py
```

Start the dashboard in a second terminal:

```bash
cd frontend
npm run dev
```

The API is available at `http://localhost:8000`, with interactive API docs at
`http://localhost:8000/docs`. The dashboard runs at `http://localhost:3000`.

## Checks

```bash
cd backend && uv run pytest && uv run ruff check .
cd frontend && npm run lint && npm run build
```
