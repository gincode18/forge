# ADR 0002: Correlate HTTP requests with queued runs

## Context

Phase 1 persists queued runs and an append-only `run.created` event, but a user
could not connect the HTTP request that created a run to its historical trace.
A full cross-step correlation and causation envelope belongs to the runtime and
observability phases, not the storage foundation.

## Decision

The API generates a fresh UUID for each HTTP request and returns it as
`X-Request-ID`, including for validation and resource errors. The header is
exposed to the local dashboard through CORS for ordinary API responses.
Structured resource-not-found errors also contain `request_id` in their JSON
body. Unexpected errors return a generic 500 response with a request ID,
without leaking exception details. Incoming request IDs are not trusted or
echoed.

Creating a run copies that request ID into the persisted `run.created` event
payload in the same transaction as the run. The event's existing `run_id` links
it to the durable run. Clients can therefore match the creation response header
to the trace after an API restart, without changing the Phase 1 schema.

## Alternatives

- Add correlation columns to all runs, steps, and events now. This would force a
  schema migration and preempt the Phase 5 event-envelope design.
- Reuse the run ID as the request ID. Requests without runs would lack a
  consistent identifier, and the two lifecycles would be conflated.
- Accept arbitrary caller-supplied request IDs. This risks collision and
  unbounded or untrusted input in future logs and traces.

## Consequences

`run.created` payloads now include `request_id`; older events do not, so readers
must tolerate its absence. Only run creation is durably linked to a request for
now. Later runtime events can adopt explicit correlation and causation fields
when the event contract is stabilized in Phase 5.
