import assert from "node:assert/strict";
import { test } from "node:test";
import * as trace from "../src/lib/run-trace.ts";
import { mergeEvents, streamedOutputs, modelMetrics, safeMetadata } from "../src/lib/run-trace.ts";

const event = (sequence: number, type: string, payload: Record<string, unknown>) => ({ id: String(sequence), sequence, type, payload });
test("replay is idempotent and retry resets only its step output", () => {
  const events = [event(1, "model.delta", { step_id: "one", text: "discard" }), event(2, "model.delta", { step_id: "two", text: "keep" }), event(3, "model.retry", { step_id: "one" }), event(4, "model.delta", { step_id: "one", text: "final" })];
  assert.deepEqual(streamedOutputs(mergeEvents(events, events)), { one: "final", two: "keep" });
});
test("metrics retain unknown costs and sum distinct model steps", () => {
  const steps = [{ id: "one", kind: "model", attempt: 2, output: { latency_ms: 12, usage: { input_tokens: 3, output_tokens: 4, total_tokens: 7 }, cost_usd: 0 } }, { id: "two", kind: "model", attempt: 1, output: { latency_ms: 8, usage: { total_tokens: 2 } } }];
  assert.deepEqual(modelMetrics(steps), { latency_ms: 20, input_tokens: null, output_tokens: null, total_tokens: 9, cost_usd: null, retries: 1 });
});
test("model timing falls back to valid step boundaries without inventing usage", () => {
  const steps = [{kind: "model", attempt: 1, started_at: "2026-10-01T10:00:00Z", finished_at: "2026-10-01T10:00:02Z", output: null}];
  assert.equal(modelMetrics(steps).latency_ms, 2000);
  assert.equal(modelMetrics(steps).total_tokens, null);
  assert.equal(modelMetrics(steps).cost_usd, null);
  assert.equal(modelMetrics([{...steps[0], finished_at: "invalid"}]).latency_ms, null);
  assert.equal(modelMetrics([{...steps[0], output: {latency_ms: 0}}]).latency_ms, 0);
});
test("zero is a known metric and missing metrics are not zero", () => {
  assert.equal(modelMetrics([{ kind: "model", attempt: 1, output: { cost_usd: 0 } }]).cost_usd, 0);
  assert.equal(modelMetrics([]).cost_usd, null);
});
test("three attempts count as two retries, not three", () => {
  const steps = [1, 2, 3].map((attempt) => ({ kind: "model", attempt, output: null }));
  assert.equal(modelMetrics(steps).retries, 2);
});
test("metadata removes credential-shaped fields recursively", () => {
  assert.deepEqual(safeMetadata({ request_id: "ok", nested: { api_key: "synthetic", Authorization: "synthetic", count: 1 } }), { request_id: "ok", nested: { api_key: "[redacted]", Authorization: "[redacted]", count: 1 } });
});

test("timeline filters preserve sequence order, group policy with tools and include recoverable errors", () => {
  const filter = (trace as unknown as { filterEvents: (events: ReturnType<typeof event>[], category: string) => ReturnType<typeof event>[] }).filterEvents;
  assert.equal(typeof filter, "function");
  const events = [event(6, "run.failed", {}), event(2, "tool.policy", {}), event(5, "tool.denied", {}), event(1, "model.completed", {}), event(4, "approval.resolved", {}), event(3, "planner.decided", {})];
  for (const [category, expected] of [["All", [1,2,3,4,5,6]], ["Models", [1]], ["Planner", [3]], ["Tools", [2,5]], ["Approvals", [4]], ["Errors", [5,6]]] as const) {
    assert.deepEqual(filter(events, category).map(item => item.sequence), expected);
  }
  assert.equal(events[0].sequence, 6, "does not mutate input");
});

test("diagnosis uses terminal reason and explicit step or call identity, never the last failed step", () => {
  const diagnose = (trace as unknown as { diagnoseRun: (run: {status: string}, events: ReturnType<typeof event>[], steps: {id: string; kind: string; status: string; input: Record<string, unknown>; error: Record<string, unknown> | null}[]) => {title: string; reason: string; action: string; stepId: string | null} | null }).diagnoseRun;
  assert.equal(typeof diagnose, "function");
  const steps = [{ id: "denied", kind: "tool", status: "failed", input: {call_id: "call-1"}, error: {reason: "denied"} }, {id: "actual", kind: "model", status: "failed", input: {}, error: {message: "Provider unavailable"}}];
  const events = [event(1, "tool.denied", {step_id: "denied"}), event(2, "model.completed", {}), event(3, "run.failed", {reason: "max_steps"})];
  const budget = diagnose({status: "failed"}, events, steps)!;
  assert.equal(budget.stepId, null);
  assert.match(budget.reason, /step limit/i);
  assert.match(budget.action, /max_steps/);
  const explicit = diagnose({status: "failed"}, [event(4, "run.failed", {reason: "error", step_id: "actual"})], steps)!;
  assert.equal(explicit.stepId, "actual");
  assert.match(explicit.reason, /Provider unavailable/);
  assert.equal(diagnose({status: "failed"}, [event(4, "run.failed", {reason: "error", call_id: "call-1"})], steps)?.stepId, "denied");
  assert.equal(diagnose({status: "failed"}, [event(4, "run.failed", {reason: "max_tokens", step_id: "missing"})], steps)?.stepId, null);
  assert.equal(diagnose({status: "completed"}, events, steps), null, "a recovered denial is not a run failure");
  for (const status of ["cancelled", "interrupted"]) {
    const outcome = diagnose({status}, [event(5, `run.${status}`, {})], steps)!;
    assert.match(outcome.title.toLowerCase(), new RegExp(status));
    assert.equal(outcome.stepId, null);
    assert.ok(outcome.action.length > 10);
  }
  assert.match(diagnose({status: "failed"}, [], steps)!.reason, /not recorded/i);
  assert.match(diagnose({status: "failed"}, [event(5, "run.failed", {reason: "new_runtime_reason"})], steps)!.reason, /new_runtime_reason/);
});

test("summary measures execution not queue time and partitions denied tool rows without fabricating unknown duration", () => {
  const summarize = (trace as unknown as { summarizeRun: (run: {status: string; updated_at?: string}, events: (ReturnType<typeof event> & {created_at?: string})[], steps: {id: string; kind: string; status: string}[]) => {duration_ms: number | null; tools: {completed: number; denied: number; failed: number}} }).summarizeRun;
  assert.equal(typeof summarize, "function");
  const events = [{...event(1, "run.created", {}), created_at: "2026-10-01T10:00:00Z"}, {...event(2, "run.started", {}), created_at: "2026-10-01T10:01:00Z"}, event(3, "tool.denied", {step_id: "denied"}), {...event(4, "run.failed", {reason: "max_steps"}), created_at: "2026-10-01T10:01:02.500Z"}];
  const steps = [{id: "done", kind: "tool", status: "completed"}, {id: "denied", kind: "tool", status: "failed"}, {id: "failed", kind: "tool", status: "failed"}, {id: "cancel", kind: "tool", status: "cancelled"}, {id: "model", kind: "model", status: "completed"}];
  assert.deepEqual(summarize({status: "failed"}, [...events, events[2]], steps), {duration_ms: 2500, tools: {completed: 1, denied: 1, failed: 1}, failures: {model: 0, planner: 0, tool: 1, total: 1}});
  assert.equal(summarize({status: "failed"}, [], steps).duration_ms, null);
  assert.equal(summarize({status: "running"}, events, steps).duration_ms, null);
  assert.equal(summarize({status: "failed", updated_at: "2026-10-01T10:01:03Z"}, events.slice(0,3), steps).duration_ms, 3000);
  assert.equal(summarize({status: "failed", updated_at: "invalid"}, events.slice(0,3), steps).duration_ms, null);
  assert.equal(summarize({status: "failed", updated_at: "2026-10-01T09:00:00Z"}, events.slice(0,3), steps).duration_ms, null);
});

test("summary counts aggregate failed boundaries and partitions denied tools", () => {
  const steps = [{id: "m", kind: "model", status: "failed"}, {id: "p", kind: "planner", status: "failed"}, {id: "t", kind: "tool", status: "failed"}, {id: "d", kind: "tool", status: "failed"}];
  const events = [{...event(1, "model.failed", {}), step_id: "m"}, event(2, "tool.denied", {step_id: "d"}), event(3, "run.failed", {})];
  assert.deepEqual(trace.summarizeRun({status: "failed"}, events, steps).failures, {model: 1, planner: 1, tool: 1, total: 3});
});

test("tool aggregates use retained envelope identity without double counting denied boundaries", () => {
  const steps = [{id: "t", kind: "tool", status: "failed"}];
  const events = [{...event(1, "tool.denied", {retained: false, reason: "retention_expired"}), step_id: "t"}];
  assert.deepEqual(trace.summarizeRun({status: "failed"}, events, steps).tools, {completed: 0, denied: 1, failed: 0});
  assert.equal(trace.summarizeRun({status: "failed"}, events, steps).failures.total, 0);
});

test("event presentation explains model, policy and planner decisions while leaving safe raw metadata intact", () => {
  const present = (trace as unknown as { describeEvent: (item: ReturnType<typeof event>) => {label: string; detail: string} }).describeEvent;
  assert.equal(typeof present, "function");
  assert.deepEqual(present(event(1, "tool.policy", {tool_name: "filesystem_write", decision: "deny", reason: "not_allowed", step_id: "s", api_key: "synthetic"})), {label: "Tool policy checked", detail: "filesystem_write · deny · not_allowed"});
  assert.deepEqual(present(event(2, "planner.decided", {action: "finish"})), {label: "Planner chose an action", detail: "finish"});
  assert.match(present(event(3, "model.completed", {provider: "fake", model: "deterministic"})).detail, /fake.*deterministic/);
  assert.deepEqual(present(event(4, "future.custom", {api_key: "synthetic"})), {label: "future.custom", detail: ""});
});

test("causal traversal reports missing, legacy and cyclic predecessors instead of inventing a complete chain", () => {
  const missing = trace.causalChain([{...event(2, "run.failed", {}), causation_id: "gone"}], "2");
  assert.match(missing.warning ?? "", /missing.*gone/i);
  const legacy = trace.causalChain([event(1, "run.failed", {})], "1");
  assert.match(legacy.warning ?? "", /legacy|not recorded/i);
  const cycle = trace.causalChain([{...event(1, "model.failed", {}), causation_id: "2"}, {...event(2, "run.failed", {}), causation_id: "1"}], "2");
  assert.match(cycle.warning ?? "", /cycle/i);
  assert.equal(cycle.events.length, 2);
  assert.equal(trace.causalChain([{...event(1, "run.failed", {}), causation_id: null, schema_version: 2}], "1").warning, null);
});

test("retained terminal identity links diagnosis while expired reasons stay explicitly unknown", () => {
  const events = [{...event(1, "run.failed", {retained: false, reason: "retention_expired"}), step_id: "m"}];
  const diagnosis = trace.diagnoseRun({status: "failed"}, events, [{id: "m", input: {}, error: null}])!;
  assert.match(diagnosis.reason, /data expired by retention/i);
  assert.equal(diagnosis.stepId, "m");
  assert.ok(!diagnosis.reason.includes("Runtime reason: retention_expired"));
});

test("retention of nested content does not erase a retained terminal budget reason", () => {
  const diagnosis = trace.diagnoseRun({status: "failed"}, [event(1, "run.failed", {reason: "max_steps", detail: {retained: false, reason: "retention_expired"}})], [])!;
  assert.match(diagnosis.reason, /step limit/i);
});

test("unknown event types and terminal reasons cannot resolve inherited object properties", () => {
  const diagnosis = trace.diagnoseRun({status: "failed"}, [event(1, "run.failed", {reason: "constructor"})], []);
  assert.match(diagnosis!.reason, /constructor/);
  assert.deepEqual(trace.describeEvent(event(2, "constructor", {})), {label: "constructor", detail: ""});
});
