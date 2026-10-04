# Forge

Local-first runtime and engineering platform for AI agents.

## Project layout

- `backend/` — FastAPI service and Forge's provider-neutral runtime.
- `frontend/` — Next.js dashboard using Shadcn UI.

## Project documents

- [`docs/forge-user-guide.md`](docs/forge-user-guide.md) — start here: dashboard
  walkthrough, agent creation, tool permissions, approvals, and developer tool authoring.
- [`scope.md`](scope.md) — vision and project philosophy.
- [`architecture.md`](architecture.md) — proposed UX and technical architecture.
- [`plan.md`](plan.md) — phased implementation roadmap and current position.
- [`docs/codebase-guide.md`](docs/codebase-guide.md) — plain-English tour of the
  code and agent harness.
- [`docs/phase-five-verification.md`](docs/phase-five-verification.md)
  — completed observability phase, test/browser evidence, and deliberate limits.
- [`docs/decisions/`](docs/decisions/) — architecture decisions and tradeoffs.

## Run locally

From the repository root, use the single local operator CLI:

```bash
./forge setup       # install locked backend and frontend dependencies
./forge dev         # run both services; Ctrl-C stops both
```

For a background session:

```bash
./forge start       # returns when API and dashboard are ready
./forge status
./forge logs --service api --follow
./forge restart
./forge stop
./forge check       # backend tests/lint and frontend lint/build
```

Requires Python 3 for the launcher, uv (backend Python >=3.12), Node.js >=20.9,
and pnpm 10. Commands resolve the repository location independently of the
current directory. Logs and supervisor state live in ignored `.forge-local/`;
override with `--state-dir` or `FORGE_LOCAL_STATE_DIR`. `start` runs development
servers, not a production deployment. Docker is not required.

Custom ports and remote browser access:

```bash
./forge start --host 0.0.0.0 --api-port 8100 --dashboard-port 3100 \
  --api-url http://forge.local:8100
```

The launcher wires the browser API URL and dashboard CORS origins. Binding to
all interfaces exposes a local operator API with no authentication: only use
this on a trusted network. The default binds to `127.0.0.1`.

For an offline smoke test, explicitly choose a separate data directory:

```bash
FORGE_DATA_DIR=/absolute/path/to/smoke-data ./forge start --offline
```

Offline mode ignores dotenv and provider keys and clears database URL overrides;
normal mode retains `backend/.env` loading. Do not point smoke tests at your
regular database. `restart` retains networking/offline options, but still reads
the invoking environment for settings such as `FORGE_DATA_DIR`.

Alternatively, start the API manually:

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
run from Agents, or queue one from Runs and select **Start run** on its
detail page. No model key is needed. The detail page streams persisted events
over SSE and shows the run status, steps, result, and cancellation controls.
The API accepts `POST /api/v1/runs/{run_id}/start` (202 on acceptance),
`POST /api/v1/runs/{run_id}/cancel`, and `GET /api/v1/runs/{run_id}/stream`
(`Last-Event-ID` or `?since=N` replays events after sequence N). No-tool fake
and Gemini versions using the bounded continue/finish `react` planner are runnable.
Set
`NEXT_PUBLIC_FORGE_API_URL` for the dashboard if the API is not at
`http://localhost:8000` (the URL must be reachable from both the browser and
the Next.js server; configure `FORGE_ALLOWED_ORIGINS` on the API for a different
dashboard origin).

### Streaming model runtime (Phase 3)

To call Gemini, put `GEMINI_API_KEY=your-key` in **`backend/.env`**, or export
it into the API process environment. `backend/.env.example` is the safe template;
`.env` is ignored by Git. Start the API from `backend/` so settings load that
directory's `.env`; restart the API after editing it. Environment variables
override the file. Never put this key in Next.js, `NEXT_PUBLIC_*`, an agent
definition, or a request. The key is masked in settings representations.

Create an agent in the dashboard using provider `gemini` and model
`gemini-3.5-flash-lite`, or submit a name, nonempty instructions, provider, and
model via `POST /api/v1/agents`; queue a run with
its `agent_id` via `POST /api/v1/runs`, then call
`POST /api/v1/runs/{run_id}/start`. Without the key, start returns 422 and
leaves the run queued. The model step persists normalized text, finish reason,
token usage, request ID, and latency. The default fake provider and test suite
remain offline and key-free. The run page displays coalesced streamed text,
latency, usage, retry attempts, and safe provider metadata. ReAct accepts plain
text as a final answer or explicit JSON continue/finish actions; enabled tools
use the controlled execution path described below. Disconnecting the browser does not
cancel the run. Restarting the backend marks abandoned runs interrupted rather
than resuming them.

Provider availability is exposed by `GET /api/v1/providers` as a configuration
boolean only, never credentials. Each immutable version stores maximum steps,
duration, output tokens per request, retries, and optional cumulative token and
estimated-cost budgets. Use **Create new immutable version** to change these;
existing runs keep their original configuration. Cost is unknown unless both
input/output USD-per-million rates are explicitly entered. Budgets are checked
after each response; they are not a provider-side hard spending cap. Unknown
usage fails closed when a token/cost budget is enabled, so an unmetered failed
request is not automatically retried under those budgets.

Local acceptance includes offline provider contracts, real Google SDK HTTP
serialization/parsing with a mock transport, migrations in both directions,
and a browser create/launch/reload smoke test. An operator-approved live Gemini
run also passed on September 30, 2026; see
[`docs/phase-three-verification.md`](docs/phase-three-verification.md) for evidence.
Future live checks remain opt-in; the offline suite alone does not prove a
particular account's key, quota, or model access.

### Controlled tools (Phase 4)

Immutable versions enable exact registry tokens: `calculator@1`,
`current_time@1`, `filesystem_read@1`, `filesystem_write@1`, and `subprocess@1`.
No tools are enabled by default. Unknown, disabled, or mismatched tokens cannot
execute. Inspect schemas and risk classifications at `GET /api/v1/tools`.

Calculator, current time, and workspace reads are low-risk. Workspace writes
and subprocess calls require a persisted approval before execution. Pending
approvals survive API restarts; approve or reject using
`POST /api/v1/approvals/{id}/resolve` with `{"approved":true}` or
`{"approved":false}`. Rejection becomes a model observation. Cancellation also
closes pending approvals. Duplicate resolution cannot execute the call again.

Filesystem paths are relative to `FORGE_DATA_DIR/workspaces/{run_id}`. Recorded
writes appear at `GET /api/v1/runs/{run_id}/artifacts`, with downloads at
`GET /api/v1/runs/{run_id}/artifacts/{artifact_id}`. Subprocess execution is
disabled unless the operator configures `FORGE_SUBPROCESS_ALLOWLIST` as a JSON
array of exact argv arrays with absolute executable paths. No shell expansion
is used; calls have a sanitized environment, workspace cwd, time/output limits,
and process-group cancellation. Allowlisting an interpreter or another powerful
program still grants that program its host permissions.

**Local restrictions are not a sandbox or a security boundary.** Do not enable
commands you would not personally run. Approval is authorization, not isolation;
containers remain deferred. A process interruption during an uncertain
side-effecting call leaves a diagnosable interrupted run rather than silently
replaying it.

Offline tool demo: enable `calculator@1` and `filesystem_write@1` on a fake
version with at least 12 maximum steps, then launch with this exact input:

```json
{"forge_script":[{"name":"calculator","arguments":{"expression":"2 + 3 * 4"}},{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"14"}}]}
```

The run pauses before writing; approving produces `answer.txt` and continues
from the tool observation. See `docs/phase-four-api-contract.md` for the full
API and event contract and `docs/phase-four-verification.md` for passing automated,
browser, CLI, and restart acceptance. Phase 4 is complete for controlled local
execution; paid live Gemini tool acceptance was not performed.

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

Frontend replay/accounting regression tests:

```bash
cd frontend && node --experimental-strip-types --test tests/run-trace.test.ts
```
