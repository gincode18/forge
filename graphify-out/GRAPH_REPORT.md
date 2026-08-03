# Graph Report - .  (2026-08-03)

## Corpus Check
- Corpus is ~9,609 words - fits in a single context window. You may not need a graph.

## Summary
- 203 nodes · 223 edges · 23 communities (16 shown, 7 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Agent Runtime Architecture
- Shadcn Component Configuration
- Frontend Runtime Dependencies
- Dashboard UI Components
- TypeScript Compiler Configuration
- Frontend Tooling Dependencies
- FastAPI Health Service
- Frontend Package Scripts
- TypeScript Project Files
- Application Window Icon
- Next.js Root Layout
- Project Vision Documents
- File Icon Semantics
- Globe Icon Semantics
- Next.js Brand Asset
- Vercel Brand Asset
- Graphify Workflow
- Local Raspberry Pi Deployment
- Frontend Agent Guidance
- ESLint Configuration
- Next.js Configuration
- PostCSS Configuration
- Python API Package

## God Nodes (most connected - your core abstractions)
1. `compilerOptions` - 16 edges
2. `cn()` - 15 edges
3. `include` - 7 edges
4. `tailwind` - 6 edges
5. `aliases` - 6 edges
6. `Runtime Execution Loop` - 6 edges
7. `scripts` - 5 edges
8. `HealthResponse` - 4 edges
9. `health()` - 4 edges
10. `Badge()` - 4 edges

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

## Communities (23 total, 7 thin omitted)

### Community 0 - "Agent Runtime Architecture"
Cohesion: 0.08
Nodes (28): Deterministic Fake Providers and Tools, Immutable Agent Versions, Purpose-Specific Memory Contract, Modular Monolith, Operator Dashboard, Planner Contract, Provider Contract, Run State Machine (+20 more)

### Community 1 - "Shadcn Component Configuration"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 2 - "Frontend Runtime Dependencies"
Cohesion: 0.10
Nodes (21): @base-ui/react, class-variance-authority, clsx, dependencies, @base-ui/react, class-variance-authority, clsx, lucide-react (+13 more)

### Community 3 - "Dashboard UI Components"
Cohesion: 0.22
Nodes (14): foundations, Badge(), badgeVariants, Button(), buttonVariants, Card(), CardAction(), CardContent() (+6 more)

### Community 4 - "TypeScript Compiler Configuration"
Cohesion: 0.11
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 5 - "Frontend Tooling Dependencies"
Cohesion: 0.12
Nodes (17): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node (+9 more)

### Community 6 - "FastAPI Health Service"
Cohesion: 0.20
Nodes (9): health(), HealthResponse, The local HTTP entry point for the Forge runtime., A stable readiness contract for local clients., Identify the service and point developers to the versioned API., Return a lightweight readiness response for the Forge dashboard., root(), BaseModel (+1 more)

### Community 7 - "Frontend Package Scripts"
Cohesion: 0.20
Nodes (9): name, packageManager, private, scripts, build, dev, lint, start (+1 more)

### Community 8 - "TypeScript Project Files"
Cohesion: 0.20
Nodes (9): exclude, include, **/*.mts, .next/dev/types/**/*.ts, next-env.d.ts, .next/types/**/*.ts, node_modules, **/*.ts (+1 more)

### Community 9 - "Application Window Icon"
Cohesion: 0.60
Nodes (5): Application Interface, Blank Window Content Area, Three Circular Window Controls, Rounded Window Frame, Application Window Icon

### Community 10 - "Next.js Root Layout"
Cohesion: 0.40
Nodes (3): geistMono, geistSans, metadata

### Community 11 - "Project Vision Documents"
Cohesion: 1.00
Nodes (4): Forge Architecture, Forge Implementation Plan, Forge, Forge Vision

### Community 12 - "File Icon Semantics"
Cohesion: 0.83
Nodes (4): Document, Folded Page Corner, File Icon, Document Text Lines

### Community 13 - "Globe Icon Semantics"
Cohesion: 0.67
Nodes (4): Geographic Coordinate Grid, Global Scope, Globe SVG Icon, World Globe

### Community 14 - "Next.js Brand Asset"
Cohesion: 0.50
Nodes (4): Next.js Web Framework, Next.js Logo, Monochrome Brand Styling, NEXT.JS Wordmark

### Community 15 - "Vercel Brand Asset"
Cohesion: 0.67
Nodes (4): Vercel Brand Identity, Minimal Geometric Brand Mark, Vercel SVG Logo, Upward-Pointing Triangle

## Knowledge Gaps
- **88 isolated node(s):** `forge-api`, `$schema`, `style`, `rsc`, `tsx` (+83 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `dependencies` connect `Frontend Runtime Dependencies` to `Frontend Package Scripts`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Why does `devDependencies` connect `Frontend Tooling Dependencies` to `Frontend Package Scripts`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `compilerOptions` connect `TypeScript Compiler Configuration` to `TypeScript Project Files`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **What connects `forge-api`, `$schema`, `style` to the rest of the system?**
  _88 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Agent Runtime Architecture` be split into smaller, more focused modules?**
  _Cohesion score 0.07671957671957672 - nodes in this community are weakly interconnected._
- **Should `Shadcn Component Configuration` be split into smaller, more focused modules?**
  _Cohesion score 0.09090909090909091 - nodes in this community are weakly interconnected._
- **Should `Frontend Runtime Dependencies` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._