# Graph Report - forge  (2026-08-13)

## Corpus Check
- 55 files · ~12,905 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 382 nodes · 579 edges · 38 communities (21 shown, 17 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 35 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cae83c3f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Runtime Execution Loop
- components.json
- dependencies
- cn
- compilerOptions
- devDependencies
- app.py
- AgentRepository
- routes/agents.py
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
- routes/runs.py
- domain/agents.py
- test_agents_and_runs.py
- ADR 0001: Python for the Forge control plane and runtime
- env.py
- events.py
- test_initial_migration_upgrades_and_downgrades
- test_health_endpoint_returns_service_and_database_metadata
- adapters/__init__.py
- sqlite/__init__.py
- api/__init__.py
- routes/__init__.py
- application/__init__.py
- domain/__init__.py

## God Nodes (most connected - your core abstractions)
1. `AgentRepository` - 21 edges
2. `AgentRecord` - 16 edges
3. `RunRepository` - 16 edges
4. `compilerOptions` - 16 edges
5. `cn()` - 15 edges
6. `AgentVersionRecord` - 12 edges
7. `RunRecord` - 12 edges
8. `ResourceNotFoundError` - 11 edges
9. `create_app()` - 10 edges
10. `Database` - 9 edges

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

## Communities (38 total, 17 thin omitted)

### Community 0 - "Runtime Execution Loop"
Cohesion: 0.08
Nodes (28): Deterministic Fake Providers and Tools, Immutable Agent Versions, Purpose-Specific Memory Contract, Modular Monolith, Operator Dashboard, Planner Contract, Provider Contract, Run State Machine (+20 more)

### Community 1 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 2 - "dependencies"
Cohesion: 0.10
Nodes (21): @base-ui/react, class-variance-authority, clsx, dependencies, @base-ui/react, class-variance-authority, clsx, lucide-react (+13 more)

### Community 3 - "cn"
Cohesion: 0.22
Nodes (14): foundations, Badge(), badgeVariants, Button(), buttonVariants, Card(), CardAction(), CardContent() (+6 more)

### Community 4 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 5 - "devDependencies"
Cohesion: 0.07
Nodes (26): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node (+18 more)

### Community 6 - "app.py"
Cohesion: 0.05
Nodes (37): Compatibility entry point for ``uv run fastapi dev main.py``., create_database_engine(), Database, _is_sqlite(), Session, Database engine, sessions, migration, and SQLite configuration., Create an engine with safe local SQLite defaults., Upgrade the configured database to the latest schema revision. (+29 more)

### Community 7 - "AgentRepository"
Cohesion: 0.09
Nodes (28): AgentRecord, AgentVersionRecord, Base, EventRecord, datetime, SQLAlchemy records for Forge's local durable state., RunRecord, utc_now() (+20 more)

### Community 8 - "routes/agents.py"
Cohesion: 0.15
Nodes (28): _agent_response(), _config(), get_agent_by_id(), get_agents(), post_agent(), post_agent_version(), get, post (+20 more)

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

### Community 23 - "routes/runs.py"
Cohesion: 0.28
Nodes (14): get_events(), get_run_by_id(), get_runs(), post_run(), get, post, SessionDependency, Queued run and persisted event endpoints. (+6 more)

### Community 24 - "domain/agents.py"
Cohesion: 0.33
Nodes (5): AgentDefinition, AgentVersion, Agent identity and immutable executable configuration., Immutable configuration captured for reproducible runs., Stable identity and human-facing metadata for an agent.

### Community 25 - "test_agents_and_runs.py"
Cohesion: 0.67
Nodes (5): create_agent(), TestClient, test_agent_versions_are_immutable_snapshots(), test_missing_agent_returns_structured_404(), test_queued_run_is_pinned_and_emits_created_event()

### Community 26 - "ADR 0001: Python for the Forge control plane and runtime"
Cohesion: 0.33
Nodes (5): ADR 0001: Python for the Forge control plane and runtime, Consequences, Context, Decision, Why Python is credible for agent harnesses

## Knowledge Gaps
- **93 isolated node(s):** `forge-api`, `Event`, `$schema`, `style`, `rsc` (+88 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentRepository` connect `AgentRepository` to `routes/agents.py`, `routes/runs.py`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `AgentRepository` (e.g. with `AgentRecord` and `AgentVersionRecord`) actually correct?**
  _`AgentRepository` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `AgentRecord` (e.g. with `AgentRepository` and `RunRepository`) actually correct?**
  _`AgentRecord` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `RunRepository` (e.g. with `AgentRecord` and `AgentVersionRecord`) actually correct?**
  _`RunRepository` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `forge-api`, `Event`, `$schema` to the rest of the system?**
  _93 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Runtime Execution Loop` be split into smaller, more focused modules?**
  _Cohesion score 0.07671957671957672 - nodes in this community are weakly interconnected._
- **Should `components.json` be split into smaller, more focused modules?**
  _Cohesion score 0.09090909090909091 - nodes in this community are weakly interconnected._