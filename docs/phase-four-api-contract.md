# Phase 4 backend API contract

All routes use `/api/v1`. Existing agent/run/provider contracts remain unchanged.

## Immutable configuration

`tools` remains `string[]`, with explicit stable version tokens: `calculator@1`,
`current_time@1`, `filesystem_read@1`, `filesystem_write@1`, `subprocess@1`.
Unversioned, unknown, disabled, or mismatched versions cannot execute. No extra
policy fields in agent requests: low-risk tools allow; filesystem writes and
subprocess require approval; invalid inputs/scope/commands deny. Every call
counts as a runtime step under existing `max_steps` and shared execution timeout.
Editing enabled tokens creates a new immutable version as before.

## Catalog

`GET /tools` → array of `{name:string, version:string, key:string,
description:string, input_schema:object, output_schema:object,
capabilities:string[], risk:"low"|"sensitive", timeout_seconds:number,
max_output_bytes:number, default_policy:"allow"|"require_approval",
security_warning:string}`. `key` is the exact configuration token.

Inputs: calculator `{expression:string}`; current_time `{}`; filesystem_read
`{path:string}`; filesystem_write `{path:string,content:string}`; subprocess
`{argv:string[]}`. Paths are relative to a per-run workspace, never arbitrary
host paths. Subprocess argv must match the operator's exact allowlist (default
empty). Local controls are **not a sandbox/security boundary**.

## Approvals

`GET /runs/{run_id}/approvals` → array of `{id:string,run_id:string,
step_id:string,tool_name:string,tool_version:string,arguments:object,
status:"pending"|"approved"|"rejected"|"cancelled",created_at:string,
resolved_at:string|null}` in creation order.

`POST /approvals/{id}/resolve` body `{approved:boolean}` → same approval object.
First resolution atomically resumes the run; duplicate/conflicting resolution
returns 409 and cannot execute twice. Rejection is a tool observation, not a run
failure. Pending approval survives API restart. Run cancellation cancels pending
approvals. Use existing cancel route and poll/refetch the run after resolving.
Run status while paused is `waiting_for_approval`.

## Artifacts

`GET /runs/{run_id}/artifacts` → array of `{id:string,run_id:string,
path:string,size_bytes:number,media_type:string,created_at:string}`.
`GET /runs/{run_id}/artifacts/{artifact_id}` → bytes with attachment filename and
recorded media type; not JSON. Only recorded workspace writes are listed; missing
or unsafe paths cannot be downloaded.

## Trace and SSE

Existing envelope and sequence-based replay remain unchanged. Added names:
`tool.requested`, `tool.policy`, `tool.started`, `tool.completed`, `tool.failed`,
`tool.denied`, `approval.requested`, `approval.resolved`, `approval.cancelled`,
`artifact.created`, `run.paused`, `run.resumed`. Tool events include `step_id`,
`tool_name`, `tool_version`, and `call_id`; request includes arguments; policy
includes `decision` and `reason`; outcome includes `output` or `error` and
`duration_ms`. Approval events include `approval_id`. Artifact events contain
artifact metadata. Existing `tool.cancelled`/`tool.interrupted` step cleanup
names are possible. Refresh approvals/artifacts on relevant events.

## Offline deterministic demo

Create a fake agent enabling `calculator@1` and `filesystem_write@1`, max_steps
at least 12. Create and start a run whose input is this exact JSON string:

```json
{"forge_script":[{"name":"calculator","arguments":{"expression":"2 + 3 * 4"}},{"name":"filesystem_write","arguments":{"path":"answer.txt","content":"14"}}]}
```

Fake requests calls in order, consumes chronological observations, then finishes
with `Fake tool script completed`. The write pauses for approval; approve it to
produce downloadable `answer.txt`. Ordinary fake inputs retain old behavior.
