import assert from "node:assert/strict";
import { test } from "node:test";
import * as trace from "../src/lib/run-trace.ts";
import { readFileSync, existsSync } from "node:fs";

test("named SSE listeners cover every phase four event and cleanup event", () => {
  const names = (trace as Record<string, unknown>).runEventTypes as string[] | undefined;
  assert.ok(names, "named SSE event registry must be shared with the inspector");
  const expected = ["tool.requested", "tool.policy", "tool.started", "tool.completed", "tool.failed", "tool.denied", "tool.cancelled", "tool.interrupted", "approval.requested", "approval.resolved", "approval.cancelled", "artifact.created", "run.paused", "run.resumed"];
  for (const name of expected) assert.ok(names.includes(name), `${name} listener missing`);
  assert.equal(new Set(names).size, names.length);
  for (const name of ["run.completed", "model.delta", "model.retry", "planner.decided"]) assert.ok(names.includes(name));
});

test("approval decisions are enabled only for a pending approval on a paused run with no command in flight", () => {
  const canResolve = (trace as Record<string, unknown>).canResolveApproval as ((approval: { status: string }, status: string, busy: boolean) => boolean) | undefined;
  assert.equal(typeof canResolve, "function", "approval state helper missing");
  assert.equal(canResolve!({ status: "pending" }, "waiting_for_approval", false), true);
  for (const status of ["approved", "rejected", "cancelled"]) assert.equal(canResolve!({ status }, "waiting_for_approval", false), false);
  for (const status of ["queued", "running", "completed", "failed", "cancelled", "interrupted"]) assert.equal(canResolve!({ status: "pending" }, status, false), false);
  assert.equal(canResolve!({ status: "pending" }, "waiting_for_approval", true), false);
});

test("inspector refreshes durable approvals and artifacts, and exposes guarded decisions and binary downloads", () => {
  const source = readFileSync(new URL("../src/app/runs/[id]/run-inspector.tsx", import.meta.url), "utf8");
  assert.match(source, /getApi<Approval\[\]>\(`\/runs\/\$\{initialRun.id\}\/approvals`\)/);
  assert.match(source, /getApi<Artifact\[\]>\(`\/runs\/\$\{initialRun.id\}\/artifacts`\)/);
  assert.match(source, /canResolveApproval\(approval, run.status,/);
  assert.match(source, /\/approvals\/\$\{approval.id\}\/resolve/);
  assert.match(source, /approved\s*\}/);
  assert.match(source, /artifactDownloadUrl\(run.id, artifact.id\)/);
  assert.match(source, /Refresh trace/);
});

test("tools catalog route displays schemas, risks, capabilities and security warning using existing navigation", () => {
  const path = new URL("../src/app/tools/page.tsx", import.meta.url);
  assert.ok(existsSync(path), "Tools catalog route missing");
  const source = readFileSync(path, "utf8");
  for (const field of ["input_schema", "output_schema", "risk", "default_policy", "capabilities", "security_warning"]) assert.ok(source.includes(`tool.${field}`), field);
  assert.match(source, /not a sandbox/);
  assert.match(readFileSync(new URL("../src/components/shell.tsx", import.meta.url), "utf8"), /href="\/tools"/);
});
