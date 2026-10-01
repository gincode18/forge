# 0006 — Controlled local tools and durable approval pauses

Status: Accepted

## Decision

The runtime alone executes the explicit, versioned built-in registry. An immutable
agent version enables exact `name@version` tokens. Unknown/disabled versions,
invalid typed inputs, unsafe scope, and non-allowlisted commands fail closed.
Low-risk tools allow; workspace writes and subprocess require operator approval.
Policy is re-evaluated on dispatch, including after approval; approval does not
bypass current scope or command checks. Calls consume the existing step budget,
with bounded inputs/outputs and per-tool timeouts under the shared run deadline.

Approval requests atomically persist the running tool step, approval, checkpoint,
and trace events before entering `waiting_for_approval`. The checkpoint contains
the remaining call batch, conversation, accounting, and remaining execution time.
Resolution has one durable winner. Rejection becomes a tool observation;
cancellation closes the active step and cancels pending approvals.

Pending approvals survive restart. A committed approved/rejected decision that
has not started dispatch is resumable. Before an approved side effect starts,
the runtime commits `execution_started`; recovery interrupts marked execution
rather than replaying it. This is **not exactly-once external side effects**:
a crash can occur before the effect, during it, or after it but before outcome
storage. The trace exposes an uncertain/interrupted outcome, not proof that an
external effect did or did not happen. Single-process supervision is assumed.

The timeout is an **execution-time budget**, not a wall-clock approval expiry.
Approval waiting and downtime do not consume the saved remaining seconds. Resume
uses that saved remainder, capped by the immutable version's timeout. A zero or
exhausted remainder fails without executing the approved tool. Each dispatched
tool is additionally bounded by its own timeout. There is no approval-wait TTL.

Subprocess is disabled by the operator's default-empty exact argv allowlist.
The executable must be an absolute path; no shell is used. The child receives a
minimal environment and workspace cwd. Cancellation/timeouts kill its process
group, but an approved executable is still arbitrary local code; detached or
otherwise escaping descendants are not an isolation guarantee.

## Filesystem controls and limitations

Validate workspace symlink ancestors **before** runtime directory creation.
Filesystem reads/writes and artifact downloads additionally walk every directory
(including workspace ancestors) with descriptor-relative `O_DIRECTORY` and
`O_NOFOLLOW`, then open the leaf with `O_NOFOLLOW`. Missing write parents are
created relative to an already-open directory descriptor. `fstat` verifies a
regular, single-link inode before reads or truncation; nonblocking open prevents
a swapped FIFO from hanging before validation. Writes enforce the byte bound
before opening/truncating. Artifact downloads use the same bounded opener and
return not-found for unsafe/missing files. These operations target POSIX hosts;
there is no weaker path-based fallback on unsupported platforms.

These controls are **not a sandbox or security boundary**. Runtime workspace
`mkdir` and subprocess cwd still use path-based calls: ancestor validation can
race with concurrent replacement before those calls. An already-open directory
can be renamed outside the logical workspace; a hardlink can be added after
`fstat`; other processes can mutate file contents concurrently. In-place writes
are not atomic or crash-durable, and artifact metadata names mutable files rather
than immutable content snapshots. Use operator-controlled local directories;
untrusted local processes require real OS/container isolation, not these checks.

## Schema rollback

Migration 0004 refuses downgrade before any DDL when approval-waiting runs,
pending approvals, or checkpoints remain, preserving revision, state, and trace.
Stop the runtime and finish/cancel live runs before rollback. Retained uncertain
checkpoints require operator reconciliation; do not delete diagnostic state just
to force rollback. Quiescent downgrade retains historical run/version/event rows
but removes Phase 4 approval/checkpoint/artifact tables. Migration preflight is
not protection against a concurrently running writer.

## Consequences

Offline deterministic fake scripts exercise the same policy, approvals, restart,
and artifacts as other providers. Paid/provider-account acceptance is separate.
The model remains a requester; the operator and runtime own authorization and
execution. Stronger isolation, external idempotency, immutable artifact storage,
and multi-process dispatch coordination remain outside this bounded local slice.
