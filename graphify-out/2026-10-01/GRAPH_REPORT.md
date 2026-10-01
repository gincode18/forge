# Graph Report - forge  (2026-09-30)

## Corpus Check
- 130 files · ~46,098 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 958 nodes · 2260 edges · 63 communities (45 shown, 18 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 235 edges (avg confidence: 0.62)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `751ddf73`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Runtime Execution Loop
- components.json
- 0004: Gemini as the first real model adapter
- run-inspector.tsx
- compilerOptions
- dependencies
- app.py
- routes/agents.py
- RunRepository
- Application Interface
- layout.tsx
- Forge Architecture
- Document
- World Globe
- Next.js Logo
- Vercel Brand Identity
- Knowledge Graph Maintenance
- Local-First Agent Platform
- Next.js Version-Specific Rules
- eslint.config.mjs
- next.config.ts
- postcss.config.mjs
- forge-api
- ports.py
- test_local_cli.py
- test_agents_and_runs.py
- ADR 0001: Python for the Forge control plane and runtime
- schemas.py
- events.py
- test_initial_migration_upgrades_and_downgrades
- Settings
- adapters/__init__.py
- sqlite/__init__.py
- api/__init__.py
- routes/__init__.py
- application/__init__.py
- domain/__init__.py
- Backend directories
- execute_fake_run
- ADR 0002: Correlate HTTP requests with queued runs
- 0003 — In-process supervision for deterministic runs
- runtime/__init__.py
- make_run
- Gemini model selection for Forge
- ToolRegistry
- local_cli.py
- 0005: Bounded no-tool planning and committed model streaming
- routes/runs.py
- test_invalid_limits_are_rejected
- env.py
- test_limits_migration_preserves_historical_versions_both_directions
- ReActPlanner
- domain/agents.py
- Phase 4 backend API contract
- 0006 — Controlled local tools and durable approval pauses
- Phase 4 verification
- Phase 3 acceptance evidence
- forge/__init__.py

## God Nodes (most connected - your core abstractions)
1. `execute_fake_run()` - 58 edges
2. `RunRepository` - 51 edges
3. `ToolRegistry` - 35 edges
4. `FinalPlanner` - 32 edges
5. `GeminiProvider` - 31 edges
6. `Settings` - 30 edges
7. `RunSupervisor` - 29 edges
8. `create_app()` - 28 edges
9. `ToolContext` - 27 edges
10. `FakeProvider` - 27 edges

## Surprising Connections (you probably didn't know these)
- `Forge as an Operating System for Agents` --semantically_similar_to--> `Runtime-Only Execution Path`  [INFERRED] [semantically similar]
  scope.md → architecture.md
- `Scale Only from Evidence` --semantically_similar_to--> `Modular Monolith`  [INFERRED] [semantically similar]
  plan.md → architecture.md
- `Explain Rather Than Hide Complexity` --semantically_similar_to--> `Trace-First Typed Events`  [INFERRED] [semantically similar]
  scope.md → architecture.md
- `Configurable Provider Layer` --semantically_similar_to--> `Provider Contract`  [INFERRED] [semantically similar]
  scope.md → architecture.md
- `main()` --calls--> `create_app()`  [INFERRED]
  scripts/local_api.py → backend/src/forge/api/app.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Vision-to-Architecture-to-Delivery** — scope_forge_vision, architecture_forge_architecture, plan_implementation_plan [EXTRACTED 1.00]
- **Inspectable Runtime Mechanisms** — architecture_runtime_execution_loop, architecture_trace_first_events, architecture_operator_dashboard, scope_explain_complexity [INFERRED 0.95]
- **First Durable Runtime Vertical Slice** — plan_phase_1_domain_storage, plan_phase_2_fake_agent, architecture_sqlite_persistence, architecture_sse_event_delivery [INFERRED 0.85]

## Communities (63 total, 18 thin omitted)

### Community 0 - "Runtime Execution Loop"
Cohesion: 0.08
Nodes (28): Deterministic Fake Providers and Tools, Immutable Agent Versions, Purpose-Specific Memory Contract, Modular Monolith, Operator Dashboard, Planner Contract, Provider Contract, Run State Machine (+20 more)

### Community 1 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 2 - "0004: Gemini as the first real model adapter"
Cohesion: 0.40
Nodes (4): 0004: Gemini as the first real model adapter, Context, Decision, Original slice and subsequent implementation

### Community 3 - "run-inspector.tsx"
Cohesion: 0.07
Nodes (52): ConfigFields(), CreateAgentForm(), LaunchRunForm(), NewVersionForm(), RunPage(), RunInspector(), terminal, RunsPage() (+44 more)

### Community 4 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 5 - "dependencies"
Cohesion: 0.04
Nodes (47): @base-ui/react, class-variance-authority, clsx, eslint, eslint-config-next, dependencies, @base-ui/react, class-variance-authority (+39 more)

### Community 6 - "app.py"
Cohesion: 0.09
Nodes (21): Compatibility entry point for ``uv run fastapi dev main.py``., create_database_engine(), Database, _is_sqlite(), Database engine, sessions, migration, and SQLite configuration., Create an engine with safe local SQLite defaults., Upgrade the configured database to the latest schema revision., Own the engine and produce short-lived transaction sessions. (+13 more)

### Community 7 - "routes/agents.py"
Cohesion: 0.26
Nodes (16): _agent_response(), _config(), get_agent_by_id(), get_agents(), post_agent(), post_agent_version(), get, post (+8 more)

### Community 8 - "RunRepository"
Cohesion: 0.06
Nodes (73): Session, AgentRecord, AgentVersionRecord, ApprovalRecord, ArtifactRecord, Base, EventRecord, datetime (+65 more)

### Community 9 - "Application Interface"
Cohesion: 0.60
Nodes (5): Application Interface, Blank Window Content Area, Three Circular Window Controls, Rounded Window Frame, Application Window Icon

### Community 10 - "layout.tsx"
Cohesion: 0.40
Nodes (3): geistMono, geistSans, metadata

### Community 11 - "Forge Architecture"
Cohesion: 1.00
Nodes (4): Forge Architecture, Forge Implementation Plan, Forge, Forge Vision

### Community 12 - "Document"
Cohesion: 0.83
Nodes (4): Document, Folded Page Corner, File Icon, Document Text Lines

### Community 13 - "World Globe"
Cohesion: 0.67
Nodes (4): Geographic Coordinate Grid, Global Scope, Globe SVG Icon, World Globe

### Community 14 - "Next.js Logo"
Cohesion: 0.50
Nodes (4): Next.js Web Framework, Next.js Logo, Monochrome Brand Styling, NEXT.JS Wordmark

### Community 15 - "Vercel Brand Identity"
Cohesion: 0.67
Nodes (4): Vercel Brand Identity, Minimal Geometric Brand Mark, Vercel SVG Logo, Upward-Pointing Triangle

### Community 23 - "ports.py"
Cohesion: 0.06
Nodes (61): FakeProvider, Scripted provider and finish-only planner for no-key runtime tests., _check_response(), _close_resources(), GeminiProvider, _metadata(), Exception, Google Gen AI adapter; secrets remain outside persisted run state. (+53 more)

### Community 24 - "test_local_cli.py"
Cohesion: 0.15
Nodes (23): offline_client(), parametrize, Gemini security boundaries, using only synthetic credentials and offline SDK…, response(), test_injected_clients_are_never_closed(), test_ordinary_sdk_failures_are_safe(), test_owned_cleanup_preserves_primary_outcome(), test_real_cancellation_and_deadline_survive_cleanup_failure() (+15 more)

### Community 25 - "test_agents_and_runs.py"
Cohesion: 0.47
Nodes (8): create_agent(), TestClient, test_agent_versions_are_immutable_snapshots(), test_missing_agent_returns_structured_404(), test_queued_run_is_pinned_and_emits_created_event(), test_run_steps_are_persisted_and_returned_in_order(), test_steps_for_missing_run_return_structured_404(), test_validation_errors_include_request_id_header()

### Community 26 - "ADR 0001: Python for the Forge control plane and runtime"
Cohesion: 0.33
Nodes (5): ADR 0001: Python for the Forge control plane and runtime, Consequences, Context, Decision, Why Python is credible for agent harnesses

### Community 27 - "schemas.py"
Cohesion: 0.17
Nodes (20): approvals(), artifacts(), catalog(), download(), get, post, Request, SessionDependency (+12 more)

### Community 29 - "events.py"
Cohesion: 0.36
Nodes (7): Event, BaseModel, Typed execution events persisted as the run trace., ToolBoundaryPayload, ToolOutcomePayload, ToolPolicyPayload, ToolRequestPayload

### Community 31 - "Settings"
Cohesion: 0.06
Nodes (61): create_app(), Create an isolated application, allowing temporary settings in tests., Path, Application configuration for the local Forge service., Settings loaded from ``FORGE_*`` environment variables., Return the absolute directory used for local Forge state., Return an explicit URL or the SQLite URL inside ``data_dir``., Settings (+53 more)

### Community 38 - "Backend directories"
Cohesion: 0.12
Nodes (15): A useful reading order, `adapters/sqlite/`, `alembic/`, `api/`, `application/`, Backend directories, `domain/`, Forge codebase guide (+7 more)

### Community 40 - "execute_fake_run"
Cohesion: 0.11
Nodes (55): execute_fake_run(), _model(), Path, Compatibility entry point for fake and real providers; no transaction spans…, FinalPlanner, Path, TestClient, test_abandoned_running_run_is_interrupted_on_restart() (+47 more)

### Community 41 - "ADR 0002: Correlate HTTP requests with queued runs"
Cohesion: 0.33
Nodes (5): ADR 0002: Correlate HTTP requests with queued runs, Alternatives, Consequences, Context, Decision

### Community 42 - "0003 — In-process supervision for deterministic runs"
Cohesion: 0.33
Nodes (5): 0003 — In-process supervision for deterministic runs, Alternatives, Consequences, Context, Decision

### Community 44 - "make_run"
Cohesion: 0.60
Nodes (4): make_run(), test_queued_run_can_start(), test_terminal_run_cannot_transition(), Run

### Community 45 - "Gemini model selection for Forge"
Cohesion: 0.50
Nodes (3): Gemini model selection for Forge, Scope, Sources

### Community 46 - "ToolRegistry"
Cohesion: 0.09
Nodes (56): Any, Run the local development service through the project script., run(), CalculatorInput, CalculatorOutput, PathInput, PolicyResult, BaseModel (+48 more)

### Community 47 - "local_cli.py"
Cohesion: 0.21
Nodes (20): child_running(), configuration(), http_ready(), launch_configuration(), logs(), main(), owned(), parser() (+12 more)

### Community 48 - "0005: Bounded no-tool planning and committed model streaming"
Cohesion: 0.29
Nodes (6): 0005: Bounded no-tool planning and committed model streaming, Alternatives and framework comparison, Consequences, Context, Decision, Verification

### Community 49 - "routes/runs.py"
Cohesion: 0.24
Nodes (17): cancel_run(), get_events(), get_run_by_id(), get_runs(), get_steps(), post_run(), get, post (+9 more)

### Community 50 - "test_invalid_limits_are_rejected"
Cohesion: 0.50
Nodes (4): parametrize, TestClient, test_invalid_limits_are_rejected(), test_limits_are_persisted_per_immutable_version()

### Community 54 - "ReActPlanner"
Cohesion: 0.19
Nodes (11): ContinueAction, FinalAction, Planner, Protocol, ToolAction, Explicit no-tool planning protocol, without hidden-reasoning requirements., ReActPlanner, test_engine_rejects_workspace_symlink_before_creating_run_directory() (+3 more)

### Community 55 - "domain/agents.py"
Cohesion: 0.22
Nodes (7): AgentDefinition, AgentVersion, Agent identity and immutable executable configuration., Stable identity and human-facing metadata for an agent., Immutable configuration captured for reproducible runs., Validate budgets without assuming provider pricing., validate_run_limits()

### Community 56 - "Phase 4 backend API contract"
Cohesion: 0.25
Nodes (7): Approvals, Artifacts, Catalog, Immutable configuration, Offline deterministic demo, Phase 4 backend API contract, Trace and SSE

### Community 57 - "0006 — Controlled local tools and durable approval pauses"
Cohesion: 0.33
Nodes (5): 0006 — Controlled local tools and durable approval pauses, Consequences, Decision, Filesystem controls and limitations, Schema rollback

### Community 58 - "Phase 4 verification"
Cohesion: 0.40
Nodes (4): Automated gates, Browser and CLI acceptance, Phase 4 verification, Scope and limitations

### Community 59 - "Phase 3 acceptance evidence"
Cohesion: 0.50
Nodes (3): Live Gemini check — September 30, 2026, Phase 3 acceptance evidence, Phase status

## Knowledge Gaps
- **143 isolated node(s):** `forge-api`, `Event`, `$schema`, `style`, `rsc` (+138 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `execute_fake_run()` connect `execute_fake_run` to `app.py`, `RunRepository`, `ToolRegistry`, `ReActPlanner`, `ports.py`, `Settings`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `RunRepository` connect `RunRepository` to `execute_fake_run`, `routes/runs.py`, `test_agents_and_runs.py`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `ToolRegistry` connect `ToolRegistry` to `RunRepository`, `execute_fake_run`, `schemas.py`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `execute_fake_run()` (e.g. with `.session()` and `.prepare()`) actually correct?**
  _`execute_fake_run()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `RunRepository` (e.g. with `AgentRecord` and `AgentVersionRecord`) actually correct?**
  _`RunRepository` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `ToolRegistry` (e.g. with `CalculatorInput` and `CalculatorOutput`) actually correct?**
  _`ToolRegistry` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `FinalPlanner` (e.g. with `FinalAction` and `ModelDelta`) actually correct?**
  _`FinalPlanner` has 7 INFERRED edges - model-reasoned connections that need verification._