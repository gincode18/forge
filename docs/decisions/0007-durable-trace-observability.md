# 0007 — Durable causal traces with local OpenTelemetry

Status: Accepted

## Decision

SQLite remains the source of truth for execution history; SDK spans are a
complement, not a second runtime or a replacement for committed events.

New events use schema version 2, with run-level `correlation_id`, optional
same-run `causation_id`, `trace_id`, and step-level `span_id`. The trace ID is
SHA-256 of the run ID, truncated to 32 hexadecimal characters; the step span
ID uses the first 16 hexadecimal characters of the step ID's SHA-256. Migration
`0005` adds nullable fields without inventing causal history for schema-1 rows.
An explicit predecessor must exist in the same run. Automatic predecessors
follow runtime semantics, not merely the immediately previous timeline row.

`forge.events` emits allowlisted JSON records only after the outer transaction
commits. Rollbacks and rolled-back savepoints do not announce persisted events.
Logs contain IDs, event type, outcome, and available duration—not prompts,
arguments, output, arbitrary exception text, credentials, or tracebacks.

The application owns an OpenTelemetry SDK provider. Each supervisor task uses
its application's provider; shutdown drains tasks before closing it. The
process-global OpenTelemetry singleton is not changed. There is no network
exporter or automatic instrumentation. `FORGE_TELEMETRY_CONSOLE_EXPORT=true`
explicitly enables local console export. Tests may attach an in-memory exporter.

Real spans time invoked model, planner, policy, and tool boundaries. Model and
executed-tool span IDs match persisted step identities. Policy spans are child
spans with distinct IDs and the same run/step attributes. A sensitive tool's
initial authorization segment is a separate `forge.tool.authorization` span;
after approval, execution uses the durable step span ID. This avoids exporting
two ended spans with the same ID when one durable step pauses and resumes.
Automatic exception events are disabled; attributes use safe normalized codes.
No retrospective span is fabricated for work from before restart.

The metrics endpoint derives measurements from committed events and normalized
steps. Unknown usage, pricing, and timings stay unknown. A policy denial is
separate from an execution failure. Elapsed run time includes approval waiting;
it is not the execution-time budget.

Retention is opt-in, terminal-run-only, and content-focused. Default settings
preserve data indefinitely. Cleanup retains envelopes, causal references,
sequence, diagnostic fields, metrics, and original execution timestamps.
Message cleanup also removes duplicated content in events. Artifact cleanup
unlinks only safely resolved recorded files and emits `artifact.expired`;
metadata remains visible and downloads return HTTP 410. Startup applies the
configured policy; the manual command previews by default and requires `--apply`
to remove content. This is not a periodic background scheduler.

The inspector follows recorded causal references, detects missing predecessors
and cycles, and highlights only explicit terminal step/call references. Timeline
DOM starts at 100 events and pages up to 500 plus one pinned expanded event;
causal chains page in groups of 100. SSE/replay remains committed-event delivery.

## Consequences and limits

- Durable traces survive restart even when no span exporter is configured.
- Completed authorization and later execution share a trace and step identity,
  but have different SDK span identities. The durable causation chain records
  the human decision between them.
- Span attributes and log records intentionally omit rich content; safe step
  and event details in the inspector remain the diagnostic source of truth.
- Retention is not secure erasure: database/WAL/backups, external log captures,
  and immutable agent-version instructions are outside its content policy.
- Artifact controls reduce local accidents; they are not an OS sandbox or a
  defense against hostile host directory renames after descriptors are opened.
- Timeline rendering is bounded, but the browser still fetches and holds replay
  state and step rows. Server-side pagination and remote telemetry collectors
  are not delivered by this phase.

Acceptance evidence: [Phase 5 verification](../phase-five-verification.md).
