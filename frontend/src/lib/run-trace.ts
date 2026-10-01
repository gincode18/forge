import type { RunEvent } from "./api";

export const runEventTypes = [
  "run.created", "run.started", "run.completed", "run.failed", "run.cancelled", "run.interrupted",
  "run.paused", "run.resumed", "run.budget_exceeded",
  "model.delta", "model.retry", "model.requested", "model.completed", "model.failed", "model.cancelled", "model.interrupted",
  "planner.started", "planner.decided", "planner.failed", "planner.cancelled", "planner.interrupted",
  "tool.requested", "tool.policy", "tool.started", "tool.completed", "tool.failed", "tool.denied", "tool.cancelled", "tool.interrupted",
  "approval.requested", "approval.resolved", "approval.cancelled", "artifact.created",
] as const;

export function canResolveApproval(approval: { status: string }, runStatus: string, busy: boolean): boolean {
  return approval.status === "pending" && runStatus === "waiting_for_approval" && !busy;
}

export function mergeEvents(current: RunEvent[], incoming: RunEvent[]): RunEvent[] {
  const bySequence = new Map(current.map((event) => [event.sequence, event]));
  for (const event of incoming) bySequence.set(event.sequence, event);
  return [...bySequence.values()].sort((a, b) => a.sequence - b.sequence);
}

export function streamedOutputs(events: RunEvent[]): Record<string, string> {
  const outputs: Record<string, string> = {};
  for (const event of mergeEvents([], events)) {
    const id = event.payload.step_id;
    if (typeof id !== "string") continue;
    if (event.type === "model.retry") outputs[id] = "";
    if (event.type === "model.delta" && typeof event.payload.text === "string") {
      outputs[id] = (outputs[id] ?? "") + event.payload.text;
    }
  }
  return outputs;
}

function numeric(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : null;
}
function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

export function modelMetrics(steps: { kind: string; attempt: number; output: Record<string, unknown> | null }[]) {
  const models = steps.filter((step) => step.kind === "model");
  const sum = (read: (output: Record<string, unknown>) => unknown) => {
    const values = models.map((step) => numeric(read(step.output ?? {})));
    return values.length && values.every((value) => value !== null) ? values.reduce<number>((total, value) => total + (value ?? 0), 0) : null;
  };
  return {
    latency_ms: sum((output) => output.latency_ms),
    input_tokens: sum((output) => object(output.usage).input_tokens),
    output_tokens: sum((output) => object(output.usage).output_tokens),
    total_tokens: sum((output) => object(output.usage).total_tokens),
    cost_usd: sum((output) => output.cost_usd),
    retries: models.filter((step) => step.attempt > 1).length,
  };
}

export function safeMetadata(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(safeMetadata);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, /api[_-]?key|authorization|secret|password|credential|access[_-]?token|refresh[_-]?token/i.test(key) ? "[redacted]" : safeMetadata(item)]));
  return value;
}
