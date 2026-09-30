# Phase 3 acceptance evidence

## Live Gemini check — September 30, 2026

An operator-approved smoke test exercised the actual Forge API, in-process
supervisor, Gemini SDK streaming adapter, no-tool ReAct planner, SQLite
persistence, and SSE delivery. Only one model request was made; retries were
disabled. The configured backend credential was consumed by Settings without
printing it or modifying any credential file. The database was isolated from
`backend/data/forge.db`.

| Observation | Actual result |
| --- | --- |
| Model | `gemini-3.5-flash-lite` |
| Run ID | `4d9eacca-ccb4-4f6f-b8b0-7ceadec5387d` |
| Immutable version ID | `2a626df3-539b-457b-a1bd-01f9acac7dfa` |
| Completed at (UTC) | `2026-09-30T10:24:07.434035+00:00` |
| Status | `completed` |
| Final result | `FORGE_LIVE_OK` |
| Model requests | 1 |
| Input tokens | 87 |
| Output tokens | 14 |
| Total tokens | 101 |
| Provider latency | 1205.729 ms |
| Finish reason | `STOP` |
| Provider request ID | `RuO8avLxL_qlqfkP4q7W-Qg` |
| Committed text delta events | 2 |
| SSE event sequences match committed events | Yes |
| Run, steps, and events identical after application restart | Yes |
| Normalized errors | None |

The actual event sequence was `run.created`, `run.started`, `model.requested`,
two `model.delta` events, `model.completed`, `planner.started`, `planner.decided`,
and `run.completed`. Assertions verified final output, single request, normal
finish reason, usage/latency, streamed deltas, and persistence after closing and
reopening the application; the command exited 0.

The test used FastAPI's in-process TestClient, not a live browser or deployed
server. Browser create/launch/metrics/reload was verified separately against the
fake provider during implementation. This live check confirms the configured
account's access to this model at the recorded time, not future quota or access.
No dollar cost is asserted: token usage is observed; billing was not inspected.

Local evidence (scratch files may be pruned):

- Script: `/Users/gincode/.hermes/cache/scratch/forge-phase3-live/smoke.py`
- Structured result: `/Users/gincode/.hermes/cache/scratch/forge-phase3-live/result.json`
- Isolated database: `/Users/gincode/.hermes/cache/scratch/forge-phase3-live/data/forge.db`

## Phase status

The remaining live-provider acceptance gate is closed. The default automated
suite remains offline/no-key; live checks require operator opt-in. Phase 4 tool
execution has not started. Phase 3 intentionally rejects tool requests with
`tool_disabled` and does not promise durable mid-step resume.
