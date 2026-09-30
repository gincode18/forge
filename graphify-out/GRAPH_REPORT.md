# Graph Report - forge  (2026-09-30)

## Corpus Check
- 102 files · ~32,111 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 727 nodes · 1582 edges · 54 communities (36 shown, 18 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 119 edges (avg confidence: 0.65)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bb7852ed`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Runtime Execution Loop
- components.json
- 0004: Gemini as the first real model adapter
- run-inspector.tsx
- compilerOptions
- dependencies
- Database
- AgentRepository
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
- GeminiProvider
- test_agents_and_runs.py
- ADR 0001: Python for the Forge control plane and runtime
- app.py
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
- config.py
- test_catalog_exposes_only_configuration_boolean
- 0005: Bounded no-tool planning and committed model streaming
- test_health.py
- test_invalid_limits_are_rejected
- env.py
- test_limits_migration_preserves_historical_versions_both_directions

## God Nodes (most connected - your core abstractions)
1. `execute_fake_run()` - 50 edges
2. `RunRepository` - 45 edges
3. `FinalPlanner` - 31 edges
4. `GeminiProvider` - 30 edges
5. `AgentRepository` - 26 edges
6. `RunSupervisor` - 26 edges
7. `new_run()` - 26 edges
8. `FakeProvider` - 24 edges
9. `trace()` - 24 edges
10. `ResourceNotFoundError` - 21 edges

## Surprising Connections (you probably didn't know these)
- `Forge as an Operating System for Agents` --semantically_similar_to--> `Runtime-Only Execution Path`  [INFERRED] [semantically similar]
  scope.md → architecture.md
- `Scale Only from Evidence` --semantically_similar_to--> `Modular Monolith`  [INFERRED] [semantically similar]
  plan.md → architecture.md
- `Explain Rather Than Hide Complexity` --semantically_similar_to--> `Trace-First Typed Events`  [INFERRED] [semantically similar]
  scope.md → architecture.md
- `Configurable Provider Layer` --semantically_similar_to--> `Provider Contract`  [INFERRED] [semantically similar]
  scope.md → architecture.md
- `test_environment_key_overrides_dotenv()` --calls--> `Settings`  [INFERRED]
  backend/tests/integration/test_gemini_runtime.py → backend/src/forge/config.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Vision-to-Architecture-to-Delivery** — scope_forge_vision, architecture_forge_architecture, plan_implementation_plan [EXTRACTED 1.00]
- **Inspectable Runtime Mechanisms** — architecture_runtime_execution_loop, architecture_trace_first_events, architecture_operator_dashboard, scope_explain_complexity [INFERRED 0.95]
- **First Durable Runtime Vertical Slice** — plan_phase_1_domain_storage, plan_phase_2_fake_agent, architecture_sqlite_persistence, architecture_sse_event_delivery [INFERRED 0.85]

## Communities (54 total, 18 thin omitted)

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
Cohesion: 0.09
Nodes (43): ConfigFields(), configFromForm(), limits, CreateAgentForm(), LaunchRunForm(), NewVersionForm(), RunPage(), eventTypes (+35 more)

### Community 4 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 5 - "dependencies"
Cohesion: 0.04
Nodes (47): @base-ui/react, class-variance-authority, clsx, eslint, eslint-config-next, dependencies, @base-ui/react, class-variance-authority (+39 more)

### Community 6 - "Database"
Cohesion: 0.14
Nodes (11): create_database_engine(), Database, _is_sqlite(), Database engine, sessions, migration, and SQLite configuration., Create an engine with safe local SQLite defaults., Own the engine and produce short-lived transaction sessions., get_session(), Request (+3 more)

### Community 7 - "AgentRepository"
Cohesion: 0.07
Nodes (46): AgentRecord, AgentVersionRecord, AgentRepository, Session, _agent_response(), _config(), get_agent_by_id(), get_agents() (+38 more)

### Community 8 - "RunRepository"
Cohesion: 0.06
Nodes (64): Session, Base, EventRecord, datetime, SQLAlchemy records for Forge's local durable state., RunRecord, StepRecord, utc_now() (+56 more)

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
Nodes (51): FakeProvider, Scripted provider and finish-only planner for no-key runtime tests., _check_response(), _close_resources(), _metadata(), Exception, Google Gen AI adapter; secrets remain outside persisted run state., _response_failure() (+43 more)

### Community 24 - "GeminiProvider"
Cohesion: 0.20
Nodes (27): GeminiProvider, offline_client(), parametrize, Gemini security boundaries, using only synthetic credentials and offline SDK…, response(), test_injected_clients_are_never_closed(), test_ordinary_sdk_failures_are_safe(), test_owned_cleanup_preserves_primary_outcome() (+19 more)

### Community 25 - "test_agents_and_runs.py"
Cohesion: 0.47
Nodes (8): create_agent(), TestClient, test_agent_versions_are_immutable_snapshots(), test_missing_agent_returns_structured_404(), test_queued_run_is_pinned_and_emits_created_event(), test_run_steps_are_persisted_and_returned_in_order(), test_steps_for_missing_run_return_structured_404(), test_validation_errors_include_request_id_header()

### Community 26 - "ADR 0001: Python for the Forge control plane and runtime"
Cohesion: 0.33
Nodes (5): ADR 0001: Python for the Forge control plane and runtime, Consequences, Context, Decision, Why Python is credible for agent harnesses

### Community 27 - "app.py"
Cohesion: 0.15
Nodes (13): Compatibility entry point for ``uv run fastapi dev main.py``., Upgrade the configured database to the latest schema revision., run_migrations(), create_app(), FastAPI application factory and local service entry point., Run the local development service through the project script., Create an isolated application, allowing temporary settings in tests., run() (+5 more)

### Community 31 - "Settings"
Cohesion: 0.18
Nodes (10): Path, Settings loaded from ``FORGE_*`` environment variables., Return the absolute directory used for local Forge state., Return an explicit URL or the SQLite URL inside ``data_dir``., Settings, test_dotenv_key_is_secret_and_reaches_supervisor(), Path, test_agents_survive_application_restart() (+2 more)

### Community 38 - "Backend directories"
Cohesion: 0.12
Nodes (15): A useful reading order, `adapters/sqlite/`, `alembic/`, `api/`, `application/`, Backend directories, `domain/`, Forge codebase guide (+7 more)

### Community 40 - "execute_fake_run"
Cohesion: 0.11
Nodes (53): execute_fake_run(), Compatibility entry point for fake and real providers; no transaction spans…, FinalPlanner, Path, TestClient, test_abandoned_running_run_is_interrupted_on_restart(), test_fake_provider_failure_leaves_durable_failed_trace(), test_fake_runtime_persists_model_step_and_final_trace() (+45 more)

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

### Community 46 - "config.py"
Cohesion: 0.25
Nodes (6): Application configuration for the local Forge service., client(), MonkeyPatch, Path, TestClient, fixture

### Community 47 - "test_catalog_exposes_only_configuration_boolean"
Cohesion: 0.33
Nodes (6): MonkeyPatch, parametrize, Path, TestClient, test_catalog_exposes_only_configuration_boolean(), test_catalog_lists_offline_defaults_without_credentials()

### Community 48 - "0005: Bounded no-tool planning and committed model streaming"
Cohesion: 0.29
Nodes (6): 0005: Bounded no-tool planning and committed model streaming, Alternatives and framework comparison, Consequences, Context, Decision, Verification

### Community 49 - "test_health.py"
Cohesion: 0.53
Nodes (5): TestClient, test_health_endpoint_returns_service_and_database_metadata(), test_request_id_is_exposed_to_dashboard_origin(), test_requests_receive_distinct_server_generated_ids(), test_unhandled_errors_keep_request_id_without_leaking_details()

### Community 50 - "test_invalid_limits_are_rejected"
Cohesion: 0.50
Nodes (4): parametrize, TestClient, test_invalid_limits_are_rejected(), test_limits_are_persisted_per_immutable_version()

## Knowledge Gaps
- **126 isolated node(s):** `forge-api`, `Event`, `$schema`, `style`, `rsc` (+121 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `execute_fake_run()` connect `execute_fake_run` to `RunRepository`, `Database`, `ports.py`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `RunRepository` connect `RunRepository` to `execute_fake_run`, `test_agents_and_runs.py`, `AgentRepository`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `GeminiProvider` connect `GeminiProvider` to `RunRepository`, `ports.py`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `execute_fake_run()` (e.g. with `.session()` and `.prepare()`) actually correct?**
  _`execute_fake_run()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `RunRepository` (e.g. with `AgentRecord` and `AgentVersionRecord`) actually correct?**
  _`RunRepository` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `FinalPlanner` (e.g. with `FinalAction` and `ModelDelta`) actually correct?**
  _`FinalPlanner` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `GeminiProvider` (e.g. with `ModelDelta` and `ModelMessage`) actually correct?**
  _`GeminiProvider` has 7 INFERRED edges - model-reasoned connections that need verification._