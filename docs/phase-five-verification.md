# Phase 5 — Trace-first observability verification

Status: Implemented and independently verified on October 3, 2026; pre-PR
verification and the retention regression fix rechecked on October 4, 2026.
This supersedes the [partial first-slice report](phase-five-first-slice-verification.md).
No Phase 5 commit, push, or PR is implied by this report.

## Delivered

- Schema-2 committed event envelopes with stable correlation/trace IDs,
  step/span linkage, semantic same-run causation, and nullable legacy fields.
- Transaction-aware, allowlisted JSON event logs; rollback/savepoint tests and
  synthetic-credential failure tests reject payload/traceback leakage.
- Actual OpenTelemetry SDK spans around model/planner/policy/tool boundaries,
  application-owned task-local providers, explicit console export, and shutdown
  after task drain. Approval pause/resume never reuses an exported span ID.
- Read-only `GET /api/v1/runs/{run_id}/metrics`: timing, usage, cost, retry,
  boundary-failure, and disjoint tool-outcome aggregates. Unknown is not zero;
  denied tools do not count as execution failures.
- Opt-in event/message/artifact retention, startup application, idempotent
  cleanup, exact overlapping-policy preview counts, and an explicit `--apply`
  command. Expired downloads return 410; diagnostic history and metrics survive.
- Inspector guidance, friendly committed timeline, filters and safe raw data,
  exact failing-step navigation, causal-chain navigation with missing/cyclic
  history warnings, bounded timeline pages, and retention/expired-artifact UI.
- Streaming previews capped at 1 MiB and at most 128 delta events per model
  attempt; the complete final response is persisted independently.

See [ADR 0007](decisions/0007-durable-trace-observability.md) for the contract
and deliberate limits.

## Automated gates independently run

From `backend/`:

```text
uv run pytest -q
328 passed, 1 warning
uv run ruff check . ../scripts
All checks passed!
uv sync --offline --locked
Locked dependency sync passed without network access.
```

From `frontend/`:

```text
node --experimental-strip-types --test tests/*.test.ts
44 tests, 44 passed, 0 failed
pnpm lint
passed
pnpm build
production compilation, TypeScript, and page generation passed
```

Coverage includes real SQLite/API behavior, schema upgrade/downgrade and legacy
row preservation, semantic predecessor validation, SSE/replay/restart,
commit-only logging, actual SDK `ReadableSpan` capture, error/cancel/budget
attribution, streaming bounds, nullable metrics, denial/failure partitioning,
retention defaults/preview/repeat/startup, and recorded-file deletion guards.
Additional lifecycle tests exercise HTTP-scheduled spans, provider closure,
approval resume ID uniqueness, and two simultaneously open application instances.

The independent pre-commit review caught tool-output content omitted by message
retention. A failing-first regression using the built-in filesystem-read and
subprocess output models now verifies removal of `content`, `stdout`, and
`stderr` through step-history reads, while retaining returncode, diagnostic
metadata, IDs, timing, usage, and latency. The full backend suite and Ruff were
rerun after this fix.

The backend warning is the installed Starlette/httpx test-client deprecation.
Node emits the existing module-type warning for direct TypeScript tests. Neither
is a failed gate; no framework migration was made merely to suppress warnings.

`graphify update .` and `git diff --check` passed. Local document links and
Markdown fences were checked in seven changed documents. Graphify warned that
`hooks.json` produced no nodes and that community labels need refreshing; the
AST graph updated, but those graph-quality warnings are not claimed resolved.

## Browser and restart acceptance

Ran an isolated offline stack through the real local launcher, Chromium, and
HTTP API on API port 18105 and dashboard port 13105. Scratch data and supervisor
state were separate from the operator database. No paid provider call was made.

Independently exercised:

1. Create an agent and launch a scripted sensitive write; pause visibly and
   reload, then restart with the pending approval intact.
2. Approve and download the resulting artifact; reject another call; recover
   from a tool failure without falsely diagnosing it as terminal failure.
3. Terminal model failure: open named failed boundary and its highlighted step;
   traverse all five recorded causal events and open a predecessor's safe debug
   details, including its trace IDs.
4. Budget exhaustion, cancellation, and queue-only creation; no guessed failed
   step on an unlinked between-step stop.
5. A 20-tool script producing 169 events: render exactly 100 initially, expand
   earlier history in sequence order, filter tools, reload, and verify metrics
   (20 completed tools, 21 model calls, measured duration, unknown cost).
6. Mobile viewport at 390 pixels: no horizontal overflow; timeline filters and
   paging controls remain usable.
7. Age a completed scratch run, apply configured retention with the real CLI,
   and read back unchanged metrics, expired artifact status, HTTP 410 download,
   visible incomplete-history notice, absent download link, and removed content.
8. Restart again: completed state, 30 persisted events, artifact bytes `14`, and
   exact terminal failed-step pointer survive.
9. Stop the stack and verify the intentional stopped-status exit code 1.

The complete browser/restart verifier exited 0 with no captured page errors.
Screenshots were reviewed for failed boundary/causal chain, retention, and mobile
layout. Local evidence and scratch scripts are under
`~/.hermes/cache/scratch/forge-phase-five-smoke/`; they are session evidence, not
portable repository fixtures. Durable regression tests are in the suites above.

## Exit criteria

- [x] A failed run can be diagnosed from its run page alone, within the recorded
  safe information; missing historical causality is shown rather than invented.
- [x] Invoked model and tool calls have measured timing and outcomes. Policy and
  planner boundaries are traced too; unknown measurements remain explicit.
- [x] Logs, spans, steps, and new events share run/step correlation identities.
- [x] Streaming does not create an unbounded event row per token.

## Boundaries, not pending Phase 5 gates

There is no default remote exporter, collector UI, automatic HTTP
instrumentation, or periodic retention scheduler. SDK spans are ephemeral unless
an exporter is attached; SQLite traces remain the durable inspector history.
The bounded timeline does not imply server-side pagination or bounded total
client replay memory. Retention is not secure erasure and excludes backups,
external log captures, and immutable executable agent configuration. Workspace
controls are still not a sandbox. Live paid-provider/account acceptance, stronger
isolation, conversation/memory, MCP, and skills loading are separate work.
