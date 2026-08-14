# ADR 0001: Python for the Forge control plane and runtime

- Status: Accepted for the initial architecture
- Date: 2026-08-13

## Context

Forge must provide a durable agent loop, provider adapters, tool execution,
planning, memory, tracing, evaluation, and a Python SDK. It should run locally
on a laptop or Raspberry Pi while remaining distributable as an open-source
platform.

TypeScript would provide one language across the web application and backend,
excellent package distribution through npm, and strong support for I/O-heavy
services. Python provides the deepest AI and scientific ecosystem, concise
runtime experimentation, Pydantic-based schemas, and natural integration with
the tools many agent authors already write in Python.

Distribution and distributed execution are separate concerns from the runtime's
implementation language. Forge can ship as a Python package, container, systemd
service, or standalone binary bundle. Remote workers communicate through stable
protocols and do not have to use the control plane's language.

## Decision

Use Python for the initial Forge API, runtime, SDK, planners, provider adapters,
tool contracts, persistence, and evaluation engine. Use TypeScript for the
Next.js operator dashboard.

Keep performance-sensitive and isolation-sensitive boundaries replaceable:

- provider adapters behind a provider protocol;
- tools behind schemas and an execution-backend protocol;
- persistence behind repositories;
- workers behind commands and events;
- HTTP and event schemas versioned independently from Python objects.

Do not plan a speculative full rewrite. Measure bottlenecks first. If profiling
finds CPU-bound runtime components, implement only those components in Rust,
Go, or another suitable language behind the existing boundary. If JavaScript
agent authors need a native SDK, generate or build a TypeScript client against
the stable Forge API rather than moving the control plane prematurely.

## Why Python is credible for agent harnesses

Agent systems are primarily network, model, subprocess, and storage orchestration;
their critical path is usually external I/O rather than interpreter throughput.
Major Python-first agent runtimes and harnesses include the OpenAI Agents SDK,
OpenHands, CrewAI, PydanticAI, and the Python implementation of LangGraph.

## Consequences

- The runtime and dashboard use different languages.
- Python packaging and deployment must be made simple through `uv`, documented
  service configuration, and later container or standalone packaging.
- CPU-bound work must not block the async event loop.
- Domain and transport contracts must not depend on Python-only serialization.
- A later TypeScript SDK is expected; a TypeScript runtime rewrite is optional,
  evidence-driven, and not part of the current roadmap.
