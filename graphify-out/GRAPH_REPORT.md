# Graph Report - forge  (2026-10-04)

## Corpus Check
- 151 files · ~66,530 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1178 nodes · 2795 edges · 96 communities (76 shown, 20 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 291 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `94c494ed`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Runtime Execution Loop
- components.json
- 0004: Gemini as the first real model adapter
- run-inspector.tsx
- compilerOptions
- dependencies
- GeminiProvider
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
- FakeProvider
- ToolRegistry
- Forge: how agents, tools, and runs actually work
- ADR 0001: Python for the Forge control plane and runtime
- ports.py
- events.py
- test_initial_migration_upgrades_and_downgrades
- wait
- adapters/__init__.py
- sqlite/__init__.py
- api/__init__.py
- routes/__init__.py
- application/__init__.py
- domain/__init__.py
- phase-five-verification.md
- execute_fake_run
- ADR 0002: Correlate HTTP requests with queued runs
- 0003 — In-process supervision for deterministic runs
- runtime/__init__.py
- routes/tools.py
- Gemini model selection for Forge
- local_cli.py
- operator-guidance.test.ts
- 0005: Bounded no-tool planning and committed model streaming
- test_local_cli.py
- test_invalid_limits_are_rejected
- gemini.py
- test_limits_migration_preserves_historical_versions_both_directions
- test_gemini_runtime.py
- test_agents_and_runs.py
- Phase 3 acceptance evidence
- forge/__init__.py
- test_gemini_sdk_transport.py
- test_trace_diagnosis.py
- Phase 5 first slice — inspector and operator guidance
- test_provider_contract.py
- Settings
- app.py
- engine.py
- config.py
- ResourceNotFoundError
- create_app
- .session
- supervisor.py
- routes/runs.py
- Database
- test_catalog_exposes_only_configuration_boolean
- StepIdGenerator
- application/metrics.py
- test_trace_migration.py
- logging.py
- RunSupervisor
- Phase 4 verification
- Backend directories
- domain/runs.py
- test_run_metrics.py
- test_telemetry.py
- Forge codebase guide
- Phase 4 backend API contract
- test_health.py
- forge-user-guide.md
- Phase 5 — Trace-first observability verification
- make_run
- env.py
- remove_recorded_file
- .resolved_data_dir
- observability/__init__.py

## God Nodes (most connected - your core abstractions)
1. `RunRepository` - 74 edges
2. `execute_fake_run()` - 74 edges
3. `Settings` - 44 edges
4. `FinalPlanner` - 42 edges
5. `ToolRegistry` - 35 edges
6. `create_app()` - 34 edges
7. `FakeProvider` - 33 edges
8. `wait()` - 33 edges
9. `GeminiProvider` - 31 edges
10. `launch()` - 30 edges

## Surprising Connections (you probably didn't know these)
- `Forge as an Operating System for Agents` --semantically_similar_to--> `Runtime-Only Execution Path`  [INFERRED] [semantically similar]
  scope.md → architecture.md
- `Scale Only from Evidence` --semantically_similar_to--> `Modular Monolith`  [INFERRED] [semantically similar]
  plan.md → architecture.md
- `Explain Rather Than Hide Complexity` --semantically_similar_to--> `Trace-First Typed Events`  [INFERRED] [semantically similar]
  scope.md → architecture.md
- `Configurable Provider Layer` --semantically_similar_to--> `Provider Contract`  [INFERRED] [semantically similar]
  scope.md → architecture.md
- `main()` --calls--> `Settings`  [INFERRED]
  scripts/local_api.py → backend/src/forge/config.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Vision-to-Architecture-to-Delivery** — scope_forge_vision, architecture_forge_architecture, plan_implementation_plan [EXTRACTED 1.00]
- **Inspectable Runtime Mechanisms** — architecture_runtime_execution_loop, architecture_trace_first_events, architecture_operator_dashboard, scope_explain_complexity [INFERRED 0.95]
- **First Durable Runtime Vertical Slice** — plan_phase_1_domain_storage, plan_phase_2_fake_agent, architecture_sqlite_persistence, architecture_sse_event_delivery [INFERRED 0.85]

## Communities (96 total, 20 thin omitted)

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
Nodes (61): ConfigFields(), CreateAgentForm(), LaunchRunForm(), NewVersionForm(), RunPage(), RunInspector(), terminal, RunsPage() (+53 more)

### Community 4 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 5 - "dependencies"
Cohesion: 0.04
Nodes (47): @base-ui/react, class-variance-authority, clsx, eslint, eslint-config-next, dependencies, @base-ui/react, class-variance-authority (+39 more)

### Community 6 - "GeminiProvider"
Cohesion: 0.36
Nodes (19): GeminiProvider, chunk(), client_for(), collect(), parametrize, Offline doubles implement the documented awaited SDK async iterator., test_complete_and_stream_keep_thought_usage_and_tool_calls(), test_completion_can_return_tool_call_without_text() (+11 more)

### Community 7 - "AgentRepository"
Cohesion: 0.09
Nodes (36): AgentRecord, AgentVersionRecord, AgentRepository, Session, _agent_response(), _config(), get_agent_by_id(), get_agents() (+28 more)

### Community 8 - "RunRepository"
Cohesion: 0.26
Nodes (6): EventRecord, RunRecord, Select only known semantic edges, never the last chronological event., RunRepository, One execution request pinned to an immutable agent version., Run

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

### Community 23 - "FakeProvider"
Cohesion: 0.17
Nodes (14): _model(), FakeProvider, Scripted provider and finish-only planner for no-key runtime tests., ModelDelta, ModelProvider, ModelResult, ModelUsage, Protocol (+6 more)

### Community 24 - "ToolRegistry"
Cohesion: 0.09
Nodes (57): Any, Run the local development service through the project script., run(), CalculatorInput, CalculatorOutput, PathInput, PolicyResult, BaseModel (+49 more)

### Community 25 - "Forge: how agents, tools, and runs actually work"
Cohesion: 0.05
Nodes (38): 10. What this UI cannot do yet, 11. Common “why is nothing happening?” cases, 12. Shortest possible summary, 1. First: why does the UX feel confusing?, 2. The mental model: six different things, 3. What each dashboard page is for, 4. Your first run: use the offline demo before Gemini, 5. Making a real agent rather than a fake demo (+30 more)

### Community 26 - "ADR 0001: Python for the Forge control plane and runtime"
Cohesion: 0.33
Nodes (5): ADR 0001: Python for the Forge control plane and runtime, Consequences, Context, Decision, Why Python is credible for agent harnesses

### Community 27 - "ports.py"
Cohesion: 0.19
Nodes (12): ContinueAction, FinalAction, Provider-neutral streaming values and planner actions., TextContentBlock, ToolAction, ToolCallContentBlock, Explicit no-tool planning protocol, without hidden-reasoning requirements., ReActPlanner (+4 more)

### Community 29 - "events.py"
Cohesion: 0.36
Nodes (7): Event, BaseModel, Typed execution events persisted as the run trace., ToolBoundaryPayload, ToolOutcomePayload, ToolPolicyPayload, ToolRequestPayload

### Community 31 - "wait"
Cohesion: 0.15
Nodes (26): test_cancelled_step_and_terminal_have_known_causal_boundaries(), parametrize, Offline acceptance edges around approvals, snapshots, and artifacts., test_artifact_download_rejects_symlink_swap_after_validation(), test_artifact_download_revalidates_record_and_filesystem(), test_concurrent_resolution_has_one_durable_winner(), parametrize, test_downgrade_refuses_live_approval_checkpoint_without_losing_diagnostics() (+18 more)

### Community 38 - "phase-five-verification.md"
Cohesion: 0.33
Nodes (3): 0007 — Durable causal traces with local OpenTelemetry, Consequences and limits, Decision

### Community 40 - "execute_fake_run"
Cohesion: 0.08
Nodes (71): execute_fake_run(), Path, Compatibility entry point for fake and real providers; no transaction spans…, FinalPlanner, Planner, Path, TestClient, test_abandoned_running_run_is_interrupted_on_restart() (+63 more)

### Community 41 - "ADR 0002: Correlate HTTP requests with queued runs"
Cohesion: 0.33
Nodes (5): ADR 0002: Correlate HTTP requests with queued runs, Alternatives, Consequences, Context, Decision

### Community 42 - "0003 — In-process supervision for deterministic runs"
Cohesion: 0.33
Nodes (5): 0003 — In-process supervision for deterministic runs, Alternatives, Consequences, Context, Decision

### Community 44 - "routes/tools.py"
Cohesion: 0.16
Nodes (22): approvals(), artifacts(), catalog(), download(), get, post, Request, SessionDependency (+14 more)

### Community 45 - "Gemini model selection for Forge"
Cohesion: 0.50
Nodes (3): Gemini model selection for Forge, Scope, Sources

### Community 46 - "local_cli.py"
Cohesion: 0.21
Nodes (20): child_running(), configuration(), http_ready(), launch_configuration(), logs(), main(), owned(), parser() (+12 more)

### Community 47 - "operator-guidance.test.ts"
Cohesion: 0.11
Nodes (11): agent, describedHelp(), Element, nodes(), require, text(), approval, artifact (+3 more)

### Community 48 - "0005: Bounded no-tool planning and committed model streaming"
Cohesion: 0.29
Nodes (6): 0005: Bounded no-tool planning and committed model streaming, Alternatives and framework comparison, Consequences, Context, Decision, Verification

### Community 49 - "test_local_cli.py"
Cohesion: 0.15
Nodes (23): offline_client(), parametrize, Gemini security boundaries, using only synthetic credentials and offline SDK…, response(), test_injected_clients_are_never_closed(), test_ordinary_sdk_failures_are_safe(), test_owned_cleanup_preserves_primary_outcome(), test_real_cancellation_and_deadline_survive_cleanup_failure() (+15 more)

### Community 50 - "test_invalid_limits_are_rejected"
Cohesion: 0.50
Nodes (4): parametrize, TestClient, test_invalid_limits_are_rejected(), test_limits_are_persisted_per_immutable_version()

### Community 51 - "gemini.py"
Cohesion: 0.24
Nodes (12): _check_response(), _close_resources(), _metadata(), Exception, Google Gen AI adapter; secrets remain outside persisted run state., _response_failure(), _ResponseFailure, _tool_calls() (+4 more)

### Community 54 - "test_gemini_runtime.py"
Cohesion: 0.20
Nodes (7): parametrize, Offline Phase 3 contract and first real-provider runtime slice., test_environment_key_overrides_dotenv(), test_fake_provider_uses_normalized_contract(), test_gemini_adapter_normalizes_sdk_response_without_network(), test_gemini_failure_never_persists_or_logs_credentials(), test_gemini_sdk_error_never_exposes_sensitive_response()

### Community 55 - "test_agents_and_runs.py"
Cohesion: 0.47
Nodes (8): create_agent(), TestClient, test_agent_versions_are_immutable_snapshots(), test_missing_agent_returns_structured_404(), test_queued_run_is_pinned_and_emits_created_event(), test_run_steps_are_persisted_and_returned_in_order(), test_steps_for_missing_run_return_structured_404(), test_validation_errors_include_request_id_header()

### Community 56 - "Phase 3 acceptance evidence"
Cohesion: 0.50
Nodes (3): Live Gemini check — September 30, 2026, Phase 3 acceptance evidence, Phase status

### Community 60 - "test_gemini_sdk_transport.py"
Cohesion: 0.33
Nodes (3): Exercise the real Google SDK wire serialization without network or credentials., test_gemini_tool_call_retains_opaque_thought_signature(), test_real_sdk_stream_preserves_chronological_context()

### Community 61 - "test_trace_diagnosis.py"
Cohesion: 0.47
Nodes (5): create_run(), parametrize, Terminal diagnosis links real failed boundaries, never unrelated budget steps., test_between_step_budget_stop_does_not_claim_a_failed_boundary(), test_terminal_failure_identifies_its_actual_failed_step()

### Community 62 - "Phase 5 first slice — inspector and operator guidance"
Cohesion: 0.40
Nodes (5): Automated verification, Browser and restart acceptance, Delivered, Not delivered / remaining Phase 5 work, Phase 5 first slice — inspector and operator guidance

### Community 63 - "test_provider_contract.py"
Cohesion: 0.50
Nodes (4): offline_gemini(), parametrize, Both providers meet the same offline, provider-neutral streaming contract., test_provider_stream_contract_is_offline_and_has_one_terminal_result()

### Community 64 - "Settings"
Cohesion: 0.17
Nodes (22): apply_retention(), compact_content(), main(), datetime, Preview by default; --apply explicitly permits destructive content cleanup., Discard content, keeping bounded timing, usage and diagnostic fields., Compact old terminal traces only; the default policy retains everything., Settings loaded from ``FORGE_*`` environment variables. (+14 more)

### Community 65 - "app.py"
Cohesion: 0.11
Nodes (15): Compatibility entry point for ``uv run fastapi dev main.py``., FastAPI application factory and local service entry point., get_session(), Request, Session, FastAPI dependencies shared by API routes., BaseModel, Run metrics queries; never execute work from HTTP handlers. (+7 more)

### Community 66 - "engine.py"
Cohesion: 0.16
Nodes (26): ApprovalRecord, ArtifactRecord, Base, datetime, SQLAlchemy records for Forge's local durable state., RunCheckpointRecord, StepRecord, utc_now() (+18 more)

### Community 67 - "config.py"
Cohesion: 0.17
Nodes (8): Application configuration for the local Forge service., Path, test_agents_survive_application_restart(), test_run_creation_request_id_survives_restart(), test_empty_settings_key_is_not_configured(), test_application_owns_and_drains_sdk_provider(), test_approval_pause_and_resume_never_reuse_exported_span_identity(), test_concurrent_applications_export_only_their_own_runtime_spans()

### Community 68 - "ResourceNotFoundError"
Cohesion: 0.23
Nodes (13): list_approvals(), Approval commands and artifact queries; short atomic storage transactions., read_artifact(), resolve_approval(), Errors raised by application use cases., ResourceNotFoundError, create_run(), get_run() (+5 more)

### Community 69 - "create_app"
Cohesion: 0.14
Nodes (17): Upgrade the configured database to the latest schema revision., run_migrations(), create_app(), Create an isolated application, allowing temporary settings in tests., client(), fixture, MonkeyPatch, Path (+9 more)

### Community 70 - ".session"
Cohesion: 0.27
Nodes (11): Session, launch(), Durable envelopes, semantic causality, and committed metadata-only logs., test_artifact_expiry_schema_and_link(), test_explicit_causation_is_validated_and_not_added_to_tool_payload(), test_nested_rollback_never_logs_discarded_events(), test_structured_logs_only_emit_committed_metadata(), test_terminal_failure_uses_explicit_step_not_last_failed_tool() (+3 more)

### Community 71 - "supervisor.py"
Cohesion: 0.19
Nodes (14): Repository implementations backed by a SQLAlchemy session., StrEnum, Typed units of work performed while executing a run., The runtime boundary represented by a step., Lifecycle state of one runtime step., One ordered, inspectable operation belonging to a run., Step, StepKind (+6 more)

### Community 72 - "routes/runs.py"
Cohesion: 0.22
Nodes (18): cancel_run(), get_events(), get_run_by_id(), get_runs(), get_steps(), post_run(), get, post (+10 more)

### Community 73 - "Database"
Cohesion: 0.20
Nodes (7): create_database_engine(), Database, _is_sqlite(), Database engine, sessions, migration, and SQLite configuration., Create an engine with safe local SQLite defaults., Own the engine and produce short-lived transaction sessions., Engine

### Community 74 - "test_catalog_exposes_only_configuration_boolean"
Cohesion: 0.33
Nodes (6): MonkeyPatch, parametrize, Path, TestClient, test_catalog_exposes_only_configuration_boolean(), test_catalog_lists_offline_defaults_without_credentials()

### Community 75 - "StepIdGenerator"
Cohesion: 0.17
Nodes (8): configure_telemetry(), Supported SDK ID hook scoped only to creation of a Forge boundary., Install an owned local provider. No exporter unless explicitly requested., StepIdGenerator, TelemetryHandle, capture(), fixture, RandomIdGenerator

### Community 76 - "application/metrics.py"
Cohesion: 0.29
Nodes (9): metrics(), get, SessionDependency, elapsed(), number(), datetime, Session, Read-only aggregate metrics from normalized steps and committed events. (+1 more)

### Community 77 - "test_trace_migration.py"
Cohesion: 0.40
Nodes (3): parametrize, Trace migration leaves legacy identities unknown and preserves all rows., test_trace_downgrade_preflights_live_approval_before_removing_columns()

### Community 78 - "logging.py"
Cohesion: 0.39
Nodes (7): _after_commit(), _after_rollback(), _after_transaction_end(), queue_event_log(), Metadata-only JSON event logs emitted after the outer transaction commits., Snapshot allowlisted fields while SQL access is still legal, not at commit., _within()

### Community 79 - "RunSupervisor"
Cohesion: 0.23
Nodes (8): InvalidRunTransition, ValueError, Raised when a run attempts an invalid state transition., Task-local injection, restored even on failure; does not own shutdown., use_provider(), _duration(), Resume only undispatched decisions; interrupt uncertain side effects., RunSupervisor

### Community 80 - "Phase 4 verification"
Cohesion: 0.40
Nodes (4): Automated gates, Browser and CLI acceptance, Phase 4 verification, Scope and limitations

### Community 81 - "Backend directories"
Cohesion: 0.25
Nodes (8): `adapters/sqlite/`, `alembic/`, `api/`, `application/`, Backend directories, `domain/`, `runtime/`, `tests/`

### Community 82 - "domain/runs.py"
Cohesion: 0.33
Nodes (5): datetime, StrEnum, Run state and transition invariants., Return a new run state after validating the transition., RunStatus

### Community 83 - "test_run_metrics.py"
Cohesion: 0.83
Nodes (3): make_run(), test_metrics_aggregate_actual_run_and_preserve_unknown_cost(), test_metrics_unknown_usage_and_failed_attempts_are_not_zero()

### Community 84 - "test_telemetry.py"
Cohesion: 0.29
Nodes (3): parametrize, Real SDK spans, owned lifecycle, deterministic correlation, and safe failures., test_boundary_never_exports_exception_text_or_events()

### Community 85 - "Forge codebase guide"
Cohesion: 0.29
Nodes (7): A useful reading order, Forge codebase guide, Frontend, How the current runtime fits, How to verify changes, Request flow in the current code, What "agent harness" means

### Community 87 - "Phase 4 backend API contract"
Cohesion: 0.29
Nodes (7): Approvals, Artifacts, Catalog, Immutable configuration, Offline deterministic demo, Phase 4 backend API contract, Trace and SSE

### Community 88 - "test_health.py"
Cohesion: 0.53
Nodes (5): TestClient, test_health_endpoint_returns_service_and_database_metadata(), test_request_id_is_exposed_to_dashboard_origin(), test_requests_receive_distinct_server_generated_ids(), test_unhandled_errors_keep_request_id_without_leaking_details()

### Community 89 - "forge-user-guide.md"
Cohesion: 0.22
Nodes (5): 0006 — Controlled local tools and durable approval pauses, Consequences, Decision, Filesystem controls and limitations, Schema rollback

### Community 91 - "Phase 5 — Trace-first observability verification"
Cohesion: 0.33
Nodes (6): Automated gates independently run, Boundaries, not pending Phase 5 gates, Browser and restart acceptance, Delivered, Exit criteria, Phase 5 — Trace-first observability verification

### Community 92 - "make_run"
Cohesion: 0.60
Nodes (4): make_run(), test_queued_run_can_start(), test_terminal_run_cannot_transition(), Run

### Community 97 - "remove_recorded_file"
Cohesion: 0.67
Nodes (3): Path, Descriptor-relative unlink; refuse traversal, symlinks and nonregular files.…, remove_recorded_file()

## Knowledge Gaps
- **191 isolated node(s):** `forge-api`, `Event`, `$schema`, `style`, `rsc` (+186 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RunRepository` connect `RunRepository` to `Settings`, `engine.py`, `ResourceNotFoundError`, `.session`, `AgentRepository`, `supervisor.py`, `routes/runs.py`, `execute_fake_run`, `routes/tools.py`, `application/metrics.py`, `RunSupervisor`, `domain/runs.py`, `test_run_metrics.py`, `test_agents_and_runs.py`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Why does `execute_fake_run()` connect `execute_fake_run` to `engine.py`, `ResourceNotFoundError`, `create_app`, `.session`, `supervisor.py`, `RunRepository`, `Database`, `RunSupervisor`, `gemini.py`, `test_run_metrics.py`, `FakeProvider`, `ToolRegistry`, `ports.py`, `test_trace_diagnosis.py`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `Settings` connect `Settings` to `app.py`, `engine.py`, `config.py`, `.resolved_data_dir`, `create_app`, `supervisor.py`, `execute_fake_run`, `Database`, `test_catalog_exposes_only_configuration_boolean`, `RunSupervisor`, `test_gemini_runtime.py`, `test_health.py`, `wait`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `RunRepository` (e.g. with `AgentRecord` and `AgentVersionRecord`) actually correct?**
  _`RunRepository` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `execute_fake_run()` (e.g. with `.session()` and `.prepare()`) actually correct?**
  _`execute_fake_run()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `Settings` (e.g. with `RunSupervisor` and `test_tool_approval_causality_survives_restart()`) actually correct?**
  _`Settings` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `FinalPlanner` (e.g. with `FinalAction` and `ModelDelta`) actually correct?**
  _`FinalPlanner` has 7 INFERRED edges - model-reasoned connections that need verification._