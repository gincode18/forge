import assert from "node:assert/strict";
import { test } from "node:test";
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
