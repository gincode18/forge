# 0005: Bounded no-tool planning and committed model streaming

## Context

The first Gemini slice completed one model turn. Phase 3 needs visible streaming,
provider-neutral results, a real continue/finish loop, retry traces, and budgets
without introducing tool execution or durable workflow recovery prematurely.
The offline/no-key suite and immutable agent versions remain requirements.

## Decision

Keep execution in the existing in-process runtime. Providers yield normalized
text deltas followed by exactly one final result. Results contain text/tool-call
content blocks, finish reason, usage, request ID, latency, and allowlisted
metadata. The Gemini adapter uses the official SDK's awaited async iterator;
blocked, truncated, malformed, and empty responses become safe provider errors.
SDK exception strings, headers, and secret-bearing chains are not persisted or
rendered in supervisor logs. Caller-injected clients remain caller-owned.

The ReAct planner accepts explicit JSON `continue`, `finish`, or `tool` actions;
ordinary text remains a final answer. It asks for action/output, not hidden
reasoning. Subsequent turns receive the original user input followed by assistant
responses and continuation observations in chronological order. Legacy
completion-only test providers receive that same history as serialized messages.
No tool is executed: JSON and native tool requests are traced and terminate with
`tool_disabled`. Tool policy, execution, and observations belong to Phase 4.

Coalesce text deltas at size/time boundaries and persist at most 128 delta events
per model attempt. SSE delivers those committed, sequenced events; browser replay
merges by sequence. The complete normalized response is always persisted on
success. HTTP handlers do not perform model/planner work, and SQLite transactions
never span asynchronous provider calls.

Agent versions store steps, duration, output cap, retries, optional cumulative
token/cost budgets, and explicit input/output USD-per-million rates. Migration
`0003` preserves historical versions with defaults. Transient normalized provider
errors may retry within the step budget and common deadline; every attempt has its
own model step and safe retry event. Failed requests have unknown usage, so an
enabled token/cost budget fails closed rather than assuming the request was free.
Unknown aggregate usage remains null, including after an unmetered failed attempt.

Cost is a user-supplied estimate, not automatic vendor pricing or a billing cap.
The runtime checks cumulative usage after each response and sends an output cap
before each request. One request can exceed the remaining run token/cost budget;
no hard provider-side spending guarantee is claimed. Prices and limits remain
part of the immutable version, never silently changed for historical runs.

## Verification

The default suite stays offline. Shared provider contracts cover fake and Gemini;
real Google SDK serialization and SSE parsing run through `httpx.MockTransport`.
Synthetic-key tests exercise construction, transport, normalization, consumption,
and cleanup failures. Runtime tests cover streaming before completion, bounded
persistence, multi-turn context, limits, retry exhaustion, cancellation/backoff,
and interrupted recovery. Migration tests exercise upgrade and downgrade with
historical data. Frontend tests cover idempotent replay and unknown-vs-zero metrics.
A real headless-browser smoke check exercises create, launch, metrics, and reload
of the persisted fake trace without using the developer's database or credentials.

A live Gemini account/model smoke test is deliberately separate and requires
operator opt-in. That acceptance gate passed on September 30, 2026 with a single
request, committed SSE replay, usage/latency, and trace preservation after restart;
see `docs/phase-three-verification.md`. Offline SDK tests by themselves do not
establish key validity, quota, or account model access.

## Alternatives and framework comparison

- Unpersisted deltas reduce SQLite writes but require a second delivery channel
  and careful replay semantics. Bounded committed deltas reuse the existing SSE
  cursor and keep the implementation inspectable on a resource-limited host.
- Importing a general orchestration framework would hide the loop this project
  is intended to teach. A small typed provider/planner boundary is sufficient.
- LangGraph's upstream README describes durable execution and human-in-the-loop
  state as core infrastructure. Forge shares explicit stateful orchestration,
  but currently marks abandoned work interrupted instead of resuming it. Durable
  checkpoints and approval state remain later phases, not promises of this loop.
  Reference: https://github.com/langchain-ai/langgraph#why-use-langgraph

## Consequences

The dashboard can configure immutable fake/Gemini versions and inspect streamed
output, usage, latency, estimated cost, retries, and safe metadata. There is no
second execution host, hidden tool execution, distributed worker, or durable
mid-step resume. Text and tool-call blocks are supported; multimodal input and
output are not part of this no-tool reference slice.
