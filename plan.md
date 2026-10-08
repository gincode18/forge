# Forge Implementation Plan

## Current position

**Current phase: Phase 5 in progress — Phase 4 remains complete.**

**Current slice: operator guidance and the first trace-inspector slice delivered and verified offline.**

The repository now contains a packaged FastAPI service, Alembic-managed SQLite
persistence, durable agent definitions and immutable versions, queued run and
event and step records, a Next.js/Shadcn dashboard with live API health and
persisted agent/run views, `uv` for Python dependencies, and pnpm for frontend
dependencies. A no-tool deterministic fake runtime executes queued runs through
an in-process supervisor, with cancellation, step/time limits, durable event
replay over SSE, and a live run inspector. Fake and Gemini providers now share
normalized streaming results. The runtime supports continue/finish decisions,
bounded transient retries, per-version step/time/output/token/cost limits, and
inspectable usage, latency, and estimated cost. The dashboard selects providers,
models, and immutable configurations. Offline tests include the real Google SDK
with a mock HTTP transport; browser smoke checks cover creation, launch, metrics,
and historical replay. An operator-approved live Gemini run passed on September
30, 2026, including usage, latency, committed SSE, and trace preservation after
application restart. See `docs/phase-three-verification.md`. Phase 4 now includes
versioned tools, fail-closed policy, durable approvals, per-run workspaces,
bounded subprocesses, downloadable artifacts, dashboard controls, and one local
operator CLI. Parent verification passed 269 backend tests, 16 frontend tests,
lint/build, and browser create/launch/approve/download/replay acceptance through
the CLI with isolated offline data. Restart preserved the completed trace and
artifact. See `docs/phase-four-verification.md`; local controls are not a sandbox.

Phase 5's first slice adds operator guidance, event filters and friendly details,
honest run/tool summaries, workspace explanations, and explicit terminal
model/planner failure-step links with highlighted error details. Combined checks
passed 272 backend tests, 30 frontend tests, lint/build, and offline browser/CLI
acceptance covering approvals, rejection, recovered tool errors, terminal errors,
budget limits, cancellation, historical replay, and restart read-back. See
`docs/phase-five-first-slice-verification.md`. Correlation/causation, structured
logging/spans, retention, and full causal-chain coverage remain outstanding.

This plan is organized around working vertical slices rather than dates. A phase
is complete only when its exit criteria pass. We should not start several future
subsystems at once.

## Delivery rules

Every phase should:

- teach one or two specific agent-platform concepts;
- produce behavior usable from API through UI where applicable;
- add automated tests for important invariants;
- emit inspectable events for new runtime behavior;
- update architecture decisions when implementation changes the design;
- keep the Raspberry Pi deployment target in mind;
- end with a short comparison against relevant framework designs.

Avoid creating empty packages for future concepts. Introduce an abstraction when
the current phase has at least one real implementation and the boundary matters.

## Phase overview

| Phase | Outcome | Status |
| --- | --- | --- |
| 0. Vision and foundation | Shared vision, local stack, repository, architecture | Complete |
| 1. Domain and storage | Durable agent versions, runs, events, and clean modules | Complete |
| 2. End-to-end fake agent | Create and run a deterministic agent through the UI | Complete |
| 3. Real model runtime | Provider adapter, streaming, planner loop, limits | Complete |
| 4. Controlled tool execution | Tool registry, policy, approval, workspace controls | Complete |
| 5. Trace-first observability | Complete live run inspector and failure debugging | In progress — first inspector slice verified |
| 6. Chat-first conversations and memory | Usable agent chat, durable threads, bounded context, then memory | Planned |
| 7. Durable workflows | Checkpoints, retries, pause/resume, branches | Planned |
| 8. Dogfood deployment | Scheduled Home Agent running continuously on Raspberry Pi | Planned |
| 9. SDK and plugins | External agent definitions and extension loading | Planned |
| 10. Evaluation engine | Repeatable datasets and configuration comparisons | Planned |
| 11. Scale only when needed | Optional Postgres, workers, containers, distributed execution | Deferred |

## Phase 0 — Vision and foundation

### Goal

Agree on what Forge is and establish a minimal local development environment.

### Completed

- Defined the project vision and engineering philosophy in `scope.md`.
- Selected Python, FastAPI, SQLite, Next.js, TypeScript, Tailwind, and Shadcn UI.
- Set up backend dependencies with `uv` and an isolated `.venv`.
- Set up the frontend with pnpm.
- Added a health endpoint and baseline backend test.
- Added a dashboard shell.
- Created the public GitHub repository.
- Proposed the product and technical design in `architecture.md`.

### Exit criteria

- [x] Backend tests and lint pass.
- [x] Frontend lint and production build pass.
- [x] API and dashboard run locally.
- [x] Vision, architecture, and plan are documented.

## Phase 1 — Backend foundation and durable domain model

### Concepts to learn

- Ports and adapters without excessive abstraction.
- Domain invariants and state machines.
- Database transactions, migrations, and repository boundaries.

### Build

1. [x] Move the backend into an installable `src/forge` package.
2. [x] Add typed application settings and a configurable Forge data directory.
3. [x] Add SQLAlchemy, SQLite, and Alembic migrations.
4. [x] Define domain types for `AgentDefinition`, `AgentVersion`, `Run`, `Step`,
   and `Event`.
5. [x] Implement and test valid run-state transitions.
6. [x] Add repositories for agents, versions, runs, and events.
7. [x] Initialize SQLite on application startup and expose database readiness.
8. [x] Add request/run correlation IDs and structured 404 responses.

### API slice

- Create and list agents.
- Create an immutable agent version.
- Create and inspect a queued run record without executing it.
- Read persisted run events.

### UI slice

- Replace the static runtime status with real API health.
- Add an Agents list and a minimal agent creation form.
- Add a Runs list showing persisted queued runs.

### Tests

- State-transition unit tests.
- Agent-version immutability tests.
- Repository tests using a temporary SQLite database.
- API tests for agent and queued-run lifecycle.

### Exit criteria

- [x] Restarting the API preserves agents and runs.
- [x] Every run references an immutable agent version.
- [x] Invalid state transitions fail deterministically.
- [x] The dashboard shows real persisted data.
- [x] No provider SDK or actual LLM call is required.

## Phase 2 — End-to-end deterministic agent

### Concepts to learn

- Runtime ownership and application orchestration.
- Dependency inversion for nondeterministic systems.
- Background task lifecycle and event delivery.

### Build

1. [x] Define provider and planner protocols; use the SQLite run repository as
   the first concrete event sink/store. Extract storage protocols when a second
   implementation needs them rather than adding unused interfaces.
2. [x] Implement a deterministic `FakeProvider` with scripted responses.
3. [x] Implement a minimal planner that can finish without tools.
4. [x] Build the first finish-only runtime path and in-process run supervisor.
5. [x] Persist run/step transitions and typed events.
6. [x] Add cancellation and runtime limits for steps and wall-clock duration.
7. [x] Add SSE event streaming with replay by sequence number.

### UI slice

- [x] Launch a fake agent from the agent page.
- [x] Follow its status live on a run detail page with SSE replay.
- [x] See the input, deterministic model response, steps, and final result.
- [x] Cancel a deliberately long fake run.

### Exit criteria

- [x] The complete path works: create agent -> start run -> stream events ->
  complete -> reload historical trace.
- [x] Disconnecting the browser does not cancel the run.
- [x] Restarting during a run marks it interrupted rather than leaving it live.
- [x] Runtime tests are deterministic and require no API key.

This phase produces the first true Forge runtime, even though its model is fake.

## Phase 3 — Real model provider and planning loop

### Decision checkpoint

Choose the first reference provider based on the model you intend to use while
dogfooding. Implement one adapter well before adding a second.

The first reference provider is Google's Gemini API with
`gemini-3.5-flash-lite`. The official SDK adapter now streams normalized text,
tool requests, usage, finish reasons, request IDs, and allowlisted metadata.
Credentials remain environment-backed. Fake and Gemini contract tests stay
offline, including real SDK wire serialization through a mock HTTP transport.
The multi-turn planner and provider-selection/metrics UI are implemented.
Phase 3's implementation is verified locally and by an explicitly opted-in live
Gemini run with the operator's credentials. Evidence is recorded in
`docs/phase-three-verification.md`; the default suite remains offline.

### Concepts to learn

- Provider normalization and streaming.
- ReAct-style planning.
- Token, cost, timeout, and retry accounting.

### Build

1. [x] Normalize messages, text/tool content blocks, deltas, tool calls, usage, and errors.
2. [x] Implement one real provider adapter using its official SDK.
3. [x] Stream coalesced committed text deltas and persist the final response.
4. [x] Implement a basic no-tool ReAct continue/finish planner behind the protocol.
5. [x] Record model inputs, outputs, latency, usage, finish reason, and retry events.
6. [x] Add immutable run limits for steps, tokens, estimated cost, and duration.
7. [x] Keep credentials and sensitive SDK headers/errors out of logs and events.

### UI slice

- [x] Configure a provider through environment-backed settings and inspect availability.
- [x] Select provider and model on creation and new immutable agent versions.
- [x] Render committed response deltas with replay-idempotent SSE handling.
- [x] Inspect normalized results and allowlisted provider metadata; never raw headers.

### Exit criteria

- [x] One real provider can complete a live no-tool agent run (Gemini, September 30, 2026).
- [x] The fake provider still passes the same contract tests.
- [x] Provider failures are normalized into clear Forge errors.
- [x] Usage and latency appear on the run page.

### Accounting and scope

Delta persistence is capped at 128 coalesced events per model attempt, not one
row per token. Every successful final response is stored. Unknown usage/cost
stays unknown, including after failed retry attempts. Enabled token/cost budgets
fail closed when usage is unavailable. Cost requires explicit per-version input
and output USD-per-million rates and is an estimate, not a billing guarantee:
usage is checked after a response and a single request can exceed the budget.
The output cap is sent before each request. Retries count against the step budget
and share the run deadline. Tool requests are recorded but fail `tool_disabled`;
policy, execution, and observations remain Phase 4. See ADR `0005` for tradeoffs
and the comparison with durable orchestration frameworks.

## Phase 4 — Controlled tool execution

### Concepts to learn

- Schema-driven tool calling.
- Capability security and policy enforcement.
- Cancellation, timeouts, subprocesses, and output limits.
- Human-in-the-loop state transitions.

### Build

1. [x] Define the typed Tool and ToolContext contracts.
2. [x] Implement a registry with stable names and versions.
3. [x] Start with low-risk calculator and current-time tools (fake scripted runs stay deterministic).
4. [x] Add scoped filesystem read/write tools using per-run workspaces.
5. [x] Add a policy engine returning allow, deny, or require-approval decisions.
6. [x] Add persisted approval requests and resolution endpoints.
7. [x] Implement restricted local subprocess execution with explicit limits.
8. [x] Record tool request, policy decision, output, timing, and failure events.

### UI slice

- [x] Enable tools on an agent version.
- [x] Inspect tool schemas and risk classifications.
- [x] Approve or reject paused tool calls.
- [x] View file artifacts created inside the run workspace.

### Exit criteria

- [x] A model can request a tool and continue from its observation.
- [x] Disabled tools cannot execute even if the model requests them.
- [x] Sensitive actions pause durably for approval.
- [x] Tool paths reject traversal, symlinks, and unsafe opened inodes outside the assigned workspace.
- [x] Timeouts and output limits stop misbehaving tools under the local execution contract.
- [x] The UI clearly states that local restrictions are not a security boundary.

The path/output guarantees are local accident-reduction controls, not protection
against hostile concurrent host processes or escaping subprocess descendants.
ADR `0006` documents remaining races, mutable artifacts, uncertain side effects,
execution-time budgeting, and safe rollback refusal. Acceptance evidence is in
`docs/phase-four-verification.md`. No paid live tool call was required or claimed.

At the end of this phase, Forge can host a small but genuinely useful personal
agent.

## Phase 5 — Trace-first observability

### Delivered and verified

Operator guidance, sequence-ordered event filters, friendly labels/timestamps,
expandable safe payloads, elapsed duration and disjoint tool outcomes, and
explicit model/planner failure-step diagnosis are implemented. Linked failure
details open automatically; unlinked budget stops and recovered tool denials do
not invent causal steps. Workspace help distinguishes recorded artifacts from
all workspace files. See `docs/phase-five-first-slice-verification.md`.

The complete phase now includes schema-2 correlation/causation, committed safe
JSON logs, real application-owned OpenTelemetry SDK spans, aggregate metrics,
opt-in content retention, explicit causal-chain navigation, and bounded timeline
pages. Migration roundtrips, credential-safe failures, SDK lifecycle/approval
resume, and offline browser/restart acceptance are independently verified.
See `docs/phase-five-verification.md` and ADR `0007` for evidence and limits.
Remote collectors, periodic retention scheduling, server-side pagination, and
conversation/memory are not claimed as part of this local-first delivery.

### Concepts to learn

- Correlated events, logs, and spans.
- Trace visualization and failure diagnosis.
- Event delivery versus persistence guarantees.

### Build

1. Stabilize the versioned event envelope and event families.
2. Add correlation and causation IDs across runtime operations.
3. Add structured logging with consistent run and step fields.
4. Add OpenTelemetry spans around model, planner, policy, and tool boundaries.
5. Add aggregate run metrics for tokens, latency, cost, retries, and failures.
6. Add retention settings for events, messages, and artifacts.

### UI slice

- Build the full chronological run timeline.
- Add expandable model, planner, policy, tool, and error details.
- Add filters and a raw-event debug view.
- Highlight the exact failing step and causal chain.

### Exit criteria

- [x] A failed run can be diagnosed from its run page alone; missing history is explicit.
- [x] Invoked model/tool calls have timing and outcome data; unknowns remain explicit.
- [x] Logs, spans, steps, and new events share correlation identifiers.
- [x] Streaming does not create an unbounded event row per token.

## Phase 6 — Chat-first conversations and memory

### Goal

Make communicating with an agent the normal user workflow: select an agent,
open a conversation, send a task, watch its response and tool activity, and send
follow-ups without manually launching unrelated runs. Deliver usable chat before
advanced memory, summarization, or retrieval. This phase is planned, not implemented.

### Concepts to learn

- A conversation contains multiple user turns; each accepted turn has its own
  run and execution trace. A run may contain multiple model/planner/tool steps.
- Durable message history versus run-local model/tool context.
- Context-window construction, deterministic ordering, and token budgeting.
- The difference between conversation, working, and long-term memory.
- Summarization and retrieval tradeoffs after the chat workflow is usable.

### Execution contract

- Chat is an operator interface over the existing runtime, not a second model
  execution host. HTTP handlers and Next.js do not execute agent/tool work.
- A thread records its agent and selected immutable executable version. Initial
  delivery pins that version for the conversation; agent edits do not silently
  change later turns. A different version starts a new conversation initially.
- Persist each accepted user message and its run association atomically, then
  schedule through the existing supervisor. Submission retries must not create
  duplicate messages/runs. Initially allow only one active turn per thread,
  including approval-waiting turns, with server-side enforcement.
- Persist authoritative assistant replies linked to their runs. Stream previews
  remain provisional: failed/cancelled partial output must not become a successful
  reply or silently enter the next turn's context.
- Reuse committed-event delivery, bounded streaming, run limits, tool policy,
  approval resolution, cancellation, safe errors, and exact trace identities.
  Approval in chat does not grant capabilities beyond the selected version.
- Build subsequent context only from the selected thread and explicitly scoped
  memory. Display omitted, summarized, or expired history honestly; extend the
  retention contract to canonical conversation messages without resurrecting
  content from stale run previews or duplicated events.
- Preserve per-run workspace isolation. File-based follow-ups need an explicit,
  validated handoff of selected prior artifacts, not implicit shared paths or
  access to arbitrary host files. Expired artifacts remain unavailable.

### Phase 6A — First delivery: durable agent chat

Build in small API-to-UI vertical slices with failing tests first:

1. Add SQLite-backed threads, ordered user/assistant messages, and message-to-run
   associations. Test schema upgrade/downgrade and history preservation.
2. Add application use cases and HTTP APIs to create/list/reopen conversations,
   read history, and submit an idempotent user turn using the existing runtime.
   Test version pinning, thread isolation, and concurrent/duplicate submissions.
3. Add a minimal context builder that combines immutable instructions, prior
   authoritative conversation history, and the new task in deterministic order.
   Enforce configured input/output token budgets; disclose omitted history and
   reject oversized input clearly rather than silently exceeding limits.
4. Link committed assistant replies and failed/cancelled/interrupted outcomes to
   their turns. Preserve ordering and reconstruct history/live state correctly
   after reload, reconnect, approval resume, and process restart.
5. Add an agent entry point such as "Chat with agent", a conversation list,
   message history, and a composer. Sending a message starts a normal run;
   follow-ups remain in the same conversation.
6. Render streamed replies, tool activity, pending approval cards, and cancellation
   in chat. Every turn links to its existing run inspector for full diagnosis.
7. Show which context was supplied for a turn and the boundaries of artifact
   reuse. Keep task-based run launch and queue controls available for operators.

### Phase 6B — Follow-on delivery: inspectable memory

Start this slice only after the chat acceptance gate passes; completion of 6A
alone does not mark all of Phase 6 complete.

1. Add explicit working-memory records scoped to a thread or agent, with visible
   reads/writes and user controls to view and remove items.
2. Add summarization when conversation context exceeds its budget. Persist
   provenance and show which messages a summary replaces; never present it as
   the original transcript or as hidden executable instructions.
3. Define the long-term memory port without requiring a vector database, then
   implement one simple SQLite-backed text retrieval path.
4. Integrate selected memory into the bounded context builder and show what was
   read, why it was selected, and its scope. Memory cannot broaden tool permissions.

### UI acceptance workflow

Select an agent → open a conversation → send a task → watch the streamed reply
and tool activity → review any approval → send a contextual follow-up → reopen
the conversation after restart. Open any turn's run inspector when debugging.
An offline simulator remains explicitly a simulator, not a reasoning chat model.

### Exit criteria — 6A chat gate

- [ ] A user can select an agent, start a conversation, and send a task from chat.
- [ ] A follow-up supplies prior authoritative thread history to the next run;
      users need not copy earlier messages into a new task manually.
- [ ] Thread history, turn order, run links, and version pinning survive restarts.
- [ ] Each accepted turn has one traceable run; duplicate submissions and
      concurrent sends do not create unintended overlapping execution.
- [ ] Streaming, tool activity, approvals, cancellation, and failures are usable
      from chat, with a link to the exact turn's detailed run inspector.
- [ ] Failed/cancelled previews, expired content, and other threads' messages do
      not silently contaminate subsequent context.
- [ ] The context builder stays within its configured budget and exposes the
      actual selected context and any omissions.
- [ ] Chat preserves existing permissions and per-run workspace boundaries;
      artifact handoffs are explicit and validated, not implicit file sharing.
- [ ] Offline API/browser acceptance covers sending, follow-ups, reload/reconnect,
      approval, failure/cancel, duplicate sends, and restart continuity. Tests
      inspect provider inputs rather than assuming Fake reasons about language.

### Exit criteria — 6B memory and full Phase 6

- [ ] The 6A chat gate remains passing after memory integration.
- [ ] Working-memory items can be inspected and removed; reads/writes and
      retrieval choices are visible in the trace and context view.
- [ ] Summaries retain provenance and preserve the configured context budget.
- [ ] Memory is scoped and does not broaden capabilities or leak across threads.
- [ ] The runtime does not assume that all memory uses embeddings.

## Phase 7 — Durable workflows

### Concepts to learn

- Checkpointing and deterministic state transitions.
- Retry semantics, idempotency, pause/resume, and compensation.
- Sequential, conditional, loop, and parallel execution.

### Build order

1. Sequential typed workflow steps.
2. Durable checkpoints between steps.
3. Retry policies with backoff and recorded attempts.
4. Conditional branches.
5. Pause/resume and human approval as workflow states.
6. Bounded loops.
7. Parallel branches with explicit join behavior.

Do not build a visual workflow editor in this phase. Workflows begin as Python
or structured configuration so engine semantics are learned first.

### Exit criteria

- [ ] A workflow resumes from a persisted checkpoint after restart.
- [ ] Retried steps expose every attempt.
- [ ] Side-effecting steps have documented idempotency behavior.
- [ ] Branch and join behavior is deterministic and tested.

## Phase 8 — Raspberry Pi dogfood deployment

### Decision checkpoint

Choose one personal Home Agent job that is valuable every week. Keep its
capabilities small enough to audit.

### Build

1. Package API and dashboard for ARM64 local deployment.
2. Add systemd service definitions and environment configuration.
3. Add database backup and restore documentation.
4. Add schedule and webhook triggers that create normal Forge runs.
5. Add conservative CPU, memory, concurrency, and disk-retention defaults.
6. Add operational health and interrupted-run recovery.
7. Run the Home Agent continuously and record usability problems.

### Exit criteria

- [ ] Forge runs unattended on the Raspberry Pi for a meaningful trial period.
- [ ] Restarts do not lose completed traces or leave false-running state.
- [ ] Scheduled runs use the same policies and runtime as interactive runs.
- [ ] Resource use is acceptable for the device.
- [ ] Forge performs one real task well enough to replace that part of the
  existing agent setup.

## Phase 9 — SDK and plugins

### Concepts to learn

- Stable public contracts and compatibility.
- Discovery, registration, configuration, and lifecycle of extensions.

### Build

1. Extract a small public Python Agent SDK from proven internal contracts.
2. Support code-defined agent definitions and tools.
3. Add plugin discovery through Python entry points or an explicit manifest.
4. Add plugin compatibility and configuration validation.
5. Add a CLI for validate, run, inspect, and plugin listing.
6. Build one external example plugin without importing Forge internals.

### Exit criteria

- [ ] An external package can add a tool without editing Forge core.
- [ ] Invalid plugins fail safely with actionable errors.
- [ ] Public API surface is documented and intentionally small.
- [ ] Plugin loading does not grant undeclared capabilities silently.

## Phase 10 — Evaluation engine

### Concepts to learn

- Repeatability in nondeterministic systems.
- Dataset design, graders, baselines, and regression detection.

### Build

1. Define datasets, cases, expected outcomes, and run configurations.
2. Add deterministic rule-based graders first.
3. Add optional model-based graders with explicit prompts and versions.
4. Run the same dataset across agent, model, prompt, or planner versions.
5. Store evaluation results linked to ordinary Forge runs.
6. Add comparison views for quality, latency, cost, and failure rate.

### Exit criteria

- [ ] The same dataset can be rerun against two agent versions.
- [ ] Results preserve exact configuration and grader versions.
- [ ] The UI makes regressions and tradeoffs visible.

## Phase 11 — Scale only from evidence

This phase has no automatic start date. Each change needs a measured reason.

Possible upgrades:

| Observed limitation | Possible response |
| --- | --- |
| SQLite write contention | PostgreSQL adapter |
| Runs must survive API process replacement mid-step | Durable worker/queue model |
| Several machines execute runs | Distributed leases and heartbeats |
| Local subprocess controls are insufficient | Container execution backend |
| High-volume event consumers need decoupling | External event broker |
| Semantic memory volume exceeds simple retrieval | Vector index adapter |

Redis, PostgreSQL, Docker, and distributed workers should not be added merely
because production platforms use them.

## First implementation sequence

When coding begins, the first pull-sized sequence should be:

1. Refactor `backend/main.py` into `src/forge` without changing behavior.
2. Add settings and a temporary test data directory.
3. Add SQLite migrations and repository session management.
4. Implement agent and agent-version domain models.
5. Implement run states and transition tests.
6. Add agent and queued-run API endpoints.
7. Connect the dashboard health status to the real API.
8. Add Agents and Runs list pages.

Stop after this slice and review the architecture against what was learned
before beginning the fake runtime.

## Definition of done for a phase

A phase is done when:

- its exit criteria pass;
- backend lint and tests pass;
- frontend lint and production build pass when UI changed;
- database migrations are tested in both directions when schema changed;
- new runtime actions are visible through structured events;
- documentation describes any important design change;
- the feature works from a clean local setup;
- the next phase does not require guessing what the current code does.

## Ongoing backlog discipline

Ideas discovered during a phase should be recorded under the relevant future
phase instead of implemented immediately. Bugs and missing behavior that block
the active phase stay in scope. This keeps Forge aligned with its learning goal
and prevents the platform from becoming broad before its core is trustworthy.
