# Forge Implementation Plan

## Current position

**Current phase: Phase 2 complete — end-to-end deterministic agent.**

**Next phase: Phase 3 — real model provider and planning loop.**

The repository now contains a packaged FastAPI service, Alembic-managed SQLite
persistence, durable agent definitions and immutable versions, queued run and
event and step records, a Next.js/Shadcn dashboard with live API health and
persisted agent/run views, `uv` for Python dependencies, and pnpm for frontend
dependencies. A no-tool deterministic fake runtime executes queued runs through
an in-process supervisor, with cancellation, step/time limits, durable event
replay over SSE, and a live run inspector. No real provider call is required.

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
| 3. Real model runtime | Provider adapter, streaming, planner loop, limits | Planned |
| 4. Controlled tool execution | Tool registry, policy, approval, workspace controls | Planned |
| 5. Trace-first observability | Complete live run inspector and failure debugging | Planned |
| 6. Conversation and memory | Threads, context building, working memory | Planned |
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

### Concepts to learn

- Provider normalization and streaming.
- ReAct-style planning.
- Token, cost, timeout, and retry accounting.

### Build

1. Define normalized messages, content blocks, tool calls, usage, and errors.
2. Implement one real provider adapter using its official SDK.
3. Stream text deltas to connected clients while persisting the final response.
4. Implement a basic ReAct planner behind the planner protocol.
5. Record model inputs, outputs, latency, usage, finish reason, and retry events.
6. Add configurable run limits for steps, tokens, cost, and duration.
7. Redact credentials and sensitive headers from logs and events.

### UI slice

- Configure a provider through environment-backed settings.
- Select provider and model on an agent version.
- Watch a real response stream.
- Inspect normalized and raw provider metadata.

### Exit criteria

- [ ] One real provider can complete a no-tool agent run.
- [ ] The fake provider still passes the same contract tests.
- [ ] Provider failures are normalized into clear Forge errors.
- [ ] Usage and latency appear on the run page.

## Phase 4 — Controlled tool execution

### Concepts to learn

- Schema-driven tool calling.
- Capability security and policy enforcement.
- Cancellation, timeouts, subprocesses, and output limits.
- Human-in-the-loop state transitions.

### Build

1. Define the typed Tool and ToolContext contracts.
2. Implement a registry with stable names and versions.
3. Start with deterministic low-risk tools such as calculator and current time.
4. Add scoped filesystem read/write tools using per-run workspaces.
5. Add a policy engine returning allow, deny, or require-approval decisions.
6. Add persisted approval requests and resolution endpoints.
7. Implement restricted local subprocess execution with explicit limits.
8. Record tool request, policy decision, output, timing, and failure events.

### UI slice

- Enable tools on an agent version.
- Inspect tool schemas and risk classifications.
- Approve or reject paused tool calls.
- View file artifacts created inside the run workspace.

### Exit criteria

- [ ] A model can request a tool and continue from its observation.
- [ ] Disabled tools cannot execute even if the model requests them.
- [ ] Sensitive actions pause durably for approval.
- [ ] Paths cannot escape the assigned run workspace.
- [ ] Timeouts and output limits stop misbehaving tools.
- [ ] The UI clearly states that local restrictions are not a security boundary.

At the end of this phase, Forge can host a small but genuinely useful personal
agent.

## Phase 5 — Trace-first observability

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

- [ ] A failed run can be diagnosed from its run page alone.
- [ ] Every external call has timing and outcome data.
- [ ] Logs, spans, steps, and events share correlation identifiers.
- [ ] Streaming does not create an unbounded event row per token.

## Phase 6 — Conversation and memory

### Concepts to learn

- Context-window construction and token budgeting.
- The difference between conversation, working, and long-term memory.
- Summarization and retrieval tradeoffs.

### Build

1. Add threads and persisted conversation messages.
2. Implement a context builder with deterministic ordering and token limits.
3. Add explicit working-memory records scoped to a thread or agent.
4. Add summarization when conversation context exceeds its budget.
5. Define the long-term memory port without requiring a vector database.
6. Add one simple SQLite-backed text retrieval implementation.

### UI slice

- Continue a conversation across multiple runs.
- Inspect which memories were read and why.
- View and remove explicit working-memory items.
- Show the final context assembled for a model turn.

### Exit criteria

- [ ] Conversation continuity survives restarts.
- [ ] The context builder stays within a configured budget.
- [ ] Memory reads and writes are visible in the trace.
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
