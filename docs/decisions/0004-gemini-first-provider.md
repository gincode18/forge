# 0004: Gemini as the first real model adapter

## Context

Phase 2 completed a no-tool fake runtime that persists every run transition and
model/planner step. Phase 3 needs one real provider without moving execution into
HTTP handlers, storing credentials with agent versions, or making offline tests
require a key. The dogfooding model chosen for this phase is
`gemini-3.5-flash-lite`.

## Decision

Use Google's `google-genai` SDK behind the existing provider protocol. A
`gemini` agent version stores the model ID, instructions, and limits, never the
API key. Settings read `GEMINI_API_KEY` from the environment or `backend/.env`
when the API is started from `backend/`; environment variables take precedence
and the settings value uses `SecretStr`. At start the supervisor checks the key
before claiming the run; the adapter constructs an async SDK client for the invocation. Model
responses become provider-neutral text, finish reason, usage, request ID, and
latency. The runtime commits these with its model step and event. Ordinary SDK,
transport, normalization, and cleanup failures are converted to safe Forge
provider errors with suppressed raw exception chains. Cancellation and timeout
semantics are preserved; both owned SDK client halves close, while injected
clients remain caller-owned. Raw exception messages and headers are not copied
into the trace. The deterministic fake provider implements the same result
contract. Default API test settings explicitly ignore local `.env` files and
clear ambient Gemini credentials; synthetic-key regressions check persisted
errors, events, and captured supervisor logs without live calls.

## Original slice and subsequent implementation

The initial Gemini path is a single no-tool completion with the existing
finish-only planner, not a complete ReAct loop. The run limit still counts
model/planner boundaries; token, cost, retries, live text deltas, provider
settings in the dashboard, and a real multi-turn planner are remaining Phase 3
work at the time of this decision. ADR `0005` now documents their implementation
and remaining live acceptance. The result carries no invented cost estimate: prices must be versioned
and verified before cost is calculated. No transaction spans the async SDK
call. We use one vendor SDK rather than a general provider framework or an
HTTP implementation of Google's wire protocol.
