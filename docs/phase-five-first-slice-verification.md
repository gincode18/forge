# Phase 5 first slice — inspector and operator guidance

Status: First slice implemented and verified on October 3, 2026. This historical
partial report is superseded by [full Phase 5 verification](phase-five-verification.md).

## Delivered

- Agent creation, immutable versioning, per-run tasks, launch (create + start),
  and queue (create only) now have explicit operator guidance.
- Fake is identified as an offline simulator; a provider-specific scripted
  calculator example is shown without implying natural-language reasoning.
- Tool enablement, sensitive approval, subprocess allowlisting, and the read-only
  catalog are distinguished. Local execution remains explicitly not a sandbox.
- The inspector filters sequence-ordered events by All, Models, Planner, Tools,
  Approvals, and Errors; labels, timestamps, and safe raw payloads remain visible.
- Terminal diagnosis explains recorded limits/outcomes and offers a next action.
  Terminal model/planner failures now include their real `step_id`. The inspector
  names, links, highlights, and opens the explicitly linked step and metadata.
  Historical events without a pointer and between-step budget stops do not
  falsely attribute causality to the last failed/denied step.
- Summary shows elapsed start-to-terminal duration (including approval waiting,
  excluding queue time), completed/denied/failed tool counts, and existing model
  metrics. Live/invalid-timestamp duration and unpriced cost remain Unknown.
- Workspace guidance shows the run-relative directory and recorded writes;
  it does not claim to discover the operator's absolute data path or list every
  file. Each run has separate files, not an OS security boundary.

## Automated verification

Parent independently ran the combined working tree:

- `backend/: uv run pytest -q` — **272 passed**; existing Starlette/httpx warning.
- `backend/: uv run ruff check . ../scripts` — passed.
- `frontend/: node --experimental-strip-types --test tests/*.test.ts` —
  **30 passed**; existing Node module-type warnings.
- `frontend/: pnpm lint && pnpm build` — passed, including TypeScript.
- `git diff --check` — passed.

New backend tests first reproduced missing terminal step references, then passed
with the runtime change. Frontend helper and real-component hook-harness tests
cover filtering/replay, explicit causality, budget stops, unknown metrics,
workspace help, guidance, actual launch/queue handlers, and retained approvals
and artifact refresh behavior. UI guidance and inspector changes were developed
with observed failing-test → implementation → passing-test cycles.

## Browser and restart acceptance

Started the real stack through `./forge start --offline`, with isolated scratch
state/data and custom ports **18105 / 13105**. The built-in browser was blocked
by its real-profile/default-browser configuration; used isolated Playwright
Chromium without changing operator browser settings or project dependencies.

Verified through actual UI/API responses:

1. Create an agent with calculator and filesystem-write permissions; read back
   the saved tool tokens. Launch a task using the form.
2. Pause for write approval, reload, restart through the CLI, and recover the
   same pending approval.
3. Filter tool events while the run is live; approve through the UI. Completion,
   summaries, and artifact controls refresh without losing the stream.
4. Download `answer.txt`, verify exact bytes `14`, and reload historical output.
5. Timeline sequences are unique and sorted; summary records two completed tools.
6. Reject another write; it completes with one denied tool, no artifact, and no
   false terminal diagnosis.
7. A calculator division error returns an observation and the fake run completes:
   one failed tool, not a falsely failed overall run.
8. A malformed fake script fails the real model boundary. Its terminal event
   identifies the failed step; the diagnosis names it and its link targets
   highlighted, already-open error details.
9. A one-step budget failure explains `max_steps` without fabricating a failed
   boundary; a cancelled pending approval is closed and explained as cancelled.
10. Queue through the Runs form, verify queued state, then explicitly Start run.
11. Confirm read-only Tools guidance and a 390px mobile layout without page-wide
    horizontal overflow. Desktop/mobile screenshots reviewed for clipping.
12. Restart again and compare the completed run's entire persisted event list
    with the pre-restart list; artifact bytes and failed-step reference survive.
13. Stop the scratch stack and verify stopped status (the CLI's expected exit 1).

No browser page errors occurred. Acceptance identifiers in the isolated database:

- Successful run: `b2ac2467-5778-4492-bf35-619e867dd2ac` — **30 events**.
- Failed run: `56b4f111-ae33-45b7-96a6-7a380f41a9d8`.
- Explicit failed step: `a6e177dc-c757-4eeb-a13c-41934f574389`.

Scratch scripts/screenshots are under
`/Users/gincode/.hermes/cache/scratch/forge-phase-five-smoke/`; they may be pruned.
The existing isolated Playwright environment is not a repository dependency.

## Not delivered / remaining Phase 5 work

- Full correlation/causation IDs shared by logs, steps, events, and spans.
- Consistent structured runtime logging and OpenTelemetry instrumentation.
- Complete external-call timing/outcome coverage and trace-envelope stabilization.
- Retention configuration and safe cleanup for events, messages, and artifacts.
- Full causal-chain diagnosis for supervisor/tool-level failures and old traces.
- Compact/grouped or paginated timelines: long traces still require scrolling.
- Live ticking duration, project file browsing, MCP, skills, containers, memory.

No schema migration or paid Gemini calls were needed. Model error text remains
credential-safe and can intentionally be generic; the UI does not expose raw
SDK errors merely to make diagnostics more specific. Basic mobile/semantic
controls were exercised, not a full accessibility audit or all recovery paths.
