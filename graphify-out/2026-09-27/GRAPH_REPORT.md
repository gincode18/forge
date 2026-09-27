# Graph Report - forge  (2026-09-27)

## Corpus Check
- 74 files · ~18,096 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 505 nodes · 912 edges · 44 communities (27 shown, 17 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 62 edges (avg confidence: 0.68)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `535eee58`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Runtime Execution Loop
- components.json
- dependencies
- run-inspector.tsx
- compilerOptions
- devDependencies
- app.py
- RunRepository
- routes/runs.py
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
- make_run
- domain/agents.py
- test_agents_and_runs.py
- ADR 0001: Python for the Forge control plane and runtime
- env.py
- events.py
- test_initial_migration_upgrades_and_downgrades
- AgentRepository
- adapters/__init__.py
- sqlite/__init__.py
- api/__init__.py
- routes/__init__.py
- application/__init__.py
- domain/__init__.py
- Forge codebase guide
- execute_fake_run
- ADR 0002: Correlate HTTP requests with queued runs
- 0003 — In-process supervision for deterministic runs
- runtime/__init__.py

## God Nodes (most connected - your core abstractions)
1. `RunRepository` - 34 edges
2. `AgentRepository` - 25 edges
3. `ResourceNotFoundError` - 17 edges
4. `RunSupervisor` - 17 edges
5. `AgentRecord` - 16 edges
6. `RunRecord` - 16 edges
7. `execute_fake_run()` - 16 edges
8. `compilerOptions` - 16 edges
9. `Database` - 15 edges
10. `AgentVersionRecord` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Forge as an Operating System for Agents` --semantically_similar_to--> `Runtime-Only Execution Path`  [INFERRED] [semantically similar]
  scope.md → architecture.md
- `Scale Only from Evidence` --semantically_similar_to--> `Modular Monolith`  [INFERRED] [semantically similar]
  plan.md → architecture.md
- `Explain Rather Than Hide Complexity` --semantically_similar_to--> `Trace-First Typed Events`  [INFERRED] [semantically similar]
  scope.md → architecture.md
- `Configurable Provider Layer` --semantically_similar_to--> `Provider Contract`  [INFERRED] [semantically similar]
  scope.md → architecture.md
- `Local Development Workflow` --conceptually_related_to--> `Forge Dashboard`  [INFERRED]
  README.md → frontend/README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Vision-to-Architecture-to-Delivery** — scope_forge_vision, architecture_forge_architecture, plan_implementation_plan [EXTRACTED 1.00]
- **Inspectable Runtime Mechanisms** — architecture_runtime_execution_loop, architecture_trace_first_events, architecture_operator_dashboard, scope_explain_complexity [INFERRED 0.95]
- **First Durable Runtime Vertical Slice** — plan_phase_1_domain_storage, plan_phase_2_fake_agent, architecture_sqlite_persistence, architecture_sse_event_delivery [INFERRED 0.85]

## Communities (44 total, 17 thin omitted)

### Community 0 - "Runtime Execution Loop"
Cohesion: 0.08
Nodes (28): Deterministic Fake Providers and Tools, Immutable Agent Versions, Purpose-Specific Memory Contract, Modular Monolith, Operator Dashboard, Planner Contract, Provider Contract, Run State Machine (+20 more)

### Community 1 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 2 - "dependencies"
Cohesion: 0.10
Nodes (21): @base-ui/react, class-variance-authority, clsx, dependencies, @base-ui/react, class-variance-authority, clsx, lucide-react (+13 more)

### Community 3 - "run-inspector.tsx"
Cohesion: 0.13
Nodes (28): CreateAgentForm(), RunPage(), RunInspector(), terminal, RunsPage(), QueueRunForm(), Shell(), Badge() (+20 more)

### Community 4 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 5 - "devDependencies"
Cohesion: 0.07
Nodes (26): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node (+18 more)

### Community 6 - "app.py"
Cohesion: 0.05
Nodes (40): Compatibility entry point for ``uv run fastapi dev main.py``., create_database_engine(), Database, _is_sqlite(), Database engine, sessions, migration, and SQLite configuration., Create an engine with safe local SQLite defaults., Upgrade the configured database to the latest schema revision., Own the engine and produce short-lived transaction sessions. (+32 more)

### Community 7 - "RunRepository"
Cohesion: 0.09
Nodes (33): Session, EventRecord, datetime, SQLAlchemy records for Forge's local durable state., RunRecord, StepRecord, utc_now(), Repository implementations backed by a SQLAlchemy session. (+25 more)

### Community 8 - "routes/runs.py"
Cohesion: 0.16
Nodes (27): get_events(), get_run_by_id(), get_runs(), get_steps(), post_run(), get, post, Request (+19 more)

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

### Community 23 - "make_run"
Cohesion: 0.60
Nodes (4): make_run(), test_queued_run_can_start(), test_terminal_run_cannot_transition(), Run

### Community 24 - "domain/agents.py"
Cohesion: 0.33
Nodes (5): AgentDefinition, AgentVersion, Agent identity and immutable executable configuration., Immutable configuration captured for reproducible runs., Stable identity and human-facing metadata for an agent.

### Community 25 - "test_agents_and_runs.py"
Cohesion: 0.47
Nodes (8): create_agent(), TestClient, test_agent_versions_are_immutable_snapshots(), test_missing_agent_returns_structured_404(), test_queued_run_is_pinned_and_emits_created_event(), test_run_steps_are_persisted_and_returned_in_order(), test_steps_for_missing_run_return_structured_404(), test_validation_errors_include_request_id_header()

### Community 26 - "ADR 0001: Python for the Forge control plane and runtime"
Cohesion: 0.33
Nodes (5): ADR 0001: Python for the Forge control plane and runtime, Consequences, Context, Decision, Why Python is credible for agent harnesses

### Community 31 - "AgentRepository"
Cohesion: 0.12
Nodes (31): AgentRecord, AgentVersionRecord, Base, AgentRepository, Session, _agent_response(), _config(), get_agent_by_id() (+23 more)

### Community 38 - "Forge codebase guide"
Cohesion: 0.13
Nodes (14): A useful reading order, `adapters/sqlite/`, `alembic/`, `api/`, `application/`, Backend directories, `domain/`, Forge codebase guide (+6 more)

### Community 40 - "execute_fake_run"
Cohesion: 0.13
Nodes (19): execute_fake_run(), Persist each boundary; never keep a DB transaction open during a model call., FakeProvider, FinalPlanner, Scripted provider and finish-only planner for no-key runtime tests., FinalAction, ModelProvider, Planner (+11 more)

### Community 41 - "ADR 0002: Correlate HTTP requests with queued runs"
Cohesion: 0.33
Nodes (5): ADR 0002: Correlate HTTP requests with queued runs, Alternatives, Consequences, Context, Decision

### Community 42 - "0003 — In-process supervision for deterministic runs"
Cohesion: 0.33
Nodes (5): 0003 — In-process supervision for deterministic runs, Alternatives, Consequences, Context, Decision

## Knowledge Gaps
- **114 isolated node(s):** `forge-api`, `Event`, `$schema`, `style`, `rsc` (+109 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RunRepository` connect `RunRepository` to `routes/runs.py`, `test_agents_and_runs.py`, `execute_fake_run`, `AgentRepository`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `Settings` connect `app.py` to `execute_fake_run`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Why does `RunSupervisor` connect `RunRepository` to `execute_fake_run`, `app.py`, `AgentRepository`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `RunRepository` (e.g. with `AgentRecord` and `AgentVersionRecord`) actually correct?**
  _`RunRepository` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `AgentRepository` (e.g. with `AgentRecord` and `AgentVersionRecord`) actually correct?**
  _`AgentRepository` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `ResourceNotFoundError` (e.g. with `AgentConfig` and `RunSupervisor`) actually correct?**
  _`ResourceNotFoundError` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `RunSupervisor` (e.g. with `Database` and `AgentVersionRecord`) actually correct?**
  _`RunSupervisor` has 9 INFERRED edges - model-reasoned connections that need verification._