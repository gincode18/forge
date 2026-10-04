import type { RunEvent } from "./api";

export const runEventTypes = [
  "run.created", "run.started", "run.completed", "run.failed", "run.cancelled", "run.interrupted",
  "run.paused", "run.resumed", "run.budget_exceeded",
  "model.delta", "model.retry", "model.requested", "model.completed", "model.failed", "model.cancelled", "model.interrupted",
  "planner.started", "planner.decided", "planner.failed", "planner.cancelled", "planner.interrupted",
  "tool.requested", "tool.policy", "tool.started", "tool.completed", "tool.failed", "tool.denied", "tool.cancelled", "tool.interrupted",
  "approval.requested", "approval.resolved", "approval.cancelled", "artifact.created", "artifact.expired",
] as const;

export function canResolveApproval(approval: { status: string }, runStatus: string, busy: boolean): boolean {
  return approval.status === "pending" && runStatus === "waiting_for_approval" && !busy;
}

export function mergeEvents(current: RunEvent[], incoming: RunEvent[]): RunEvent[] {
  const bySequence = new Map(current.map((event) => [event.sequence, event]));
  for (const event of incoming) bySequence.set(event.sequence, event);
  return [...bySequence.values()].sort((a, b) => a.sequence - b.sequence);
}

export function dataExpired(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  if (Array.isArray(value)) return value.some(dataExpired);
  const fields = value as Record<string, unknown>;
  return (fields.retained === false && fields.reason === "retention_expired") || Object.values(fields).some(dataExpired);
}

export function streamedOutputs(events: RunEvent[]): Record<string, string> {
  const outputs: Record<string, string> = {};
  const expired = new Set(events.filter(event => event.type.startsWith("model.") && dataExpired(event.payload)).map(event => event.step_id ?? event.payload.step_id));
  for (const event of mergeEvents([], events)) {
    const id = event.step_id ?? event.payload.step_id;
    if (expired.has(id)) continue;
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

export function modelMetrics(steps: { kind: string; attempt: number; started_at?: string | null; finished_at?: string | null; output: Record<string, unknown> | null }[]) {
  const models = steps.filter((step) => step.kind === "model").map(step => {
    const start = Date.parse(step.started_at ?? "");
    const end = Date.parse(step.finished_at ?? "");
    const elapsed = Number.isFinite(start) && Number.isFinite(end) && end >= start ? end - start : null;
    return { ...step, output: { ...step.output, latency_ms: numeric(step.output?.latency_ms) ?? elapsed } };
  });
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

export const eventFilters = ["All", "Models", "Planner", "Tools", "Approvals", "Errors"] as const;
export type EventFilter = typeof eventFilters[number];
export function filterEvents(events: RunEvent[], category: EventFilter): RunEvent[] {
  const prefixes = { Models: "model.", Planner: "planner.", Tools: "tool.", Approvals: "approval." };
  return mergeEvents([], events).filter(event => category === "All" || (category === "Errors"
    ? /\.(failed|denied|budget_exceeded|interrupted)$/.test(event.type)
    : event.type.startsWith(prefixes[category])));
}

const failureReasons: Record<string, [string, string]> = {
  max_steps: ["The run reached its step limit.", "Review repeated planner/tool actions; adjust max_steps in a new agent version if needed."],
  max_tokens: ["The run reached its token budget.", "Reduce the input or adjust max_tokens in a new agent version."],
  max_cost_usd: ["The run reached its cost budget.", "Review model usage and pricing; adjust max_cost_usd in a new agent version if needed."],
  max_output_tokens: ["Model output exceeded the output token limit.", "Request a shorter answer or adjust max_output_tokens in a new agent version."],
  timeout: ["The runtime time limit was exceeded.", "Review slow model/tool calls; adjust timeout_seconds or narrow the task before starting a new run."],
  retry_exhausted: ["The provider failed after all allowed retries.", "Check provider availability and configuration before starting a new run."],
  usage_unavailable: ["Model usage was unavailable, so the runtime could not enforce its budget safely.", "Check the provider's usage reporting or budget configuration before starting a new run."],
  error: ["The runtime reported an execution error.", "Review error events and step metadata; check provider and tool configuration before starting a new run."],
};

export function causalChain(events: RunEvent[], terminalId: string) {
  const byId = new Map(events.map(event => [event.id, event]));
  const chain: RunEvent[] = [];
  const visited = new Set<string>();
  let warning: string | null = null;
  let current = byId.get(terminalId);
  if (!current) warning = `Missing terminal event: ${terminalId}.`;
  while (current) {
    if (visited.has(current.id)) { warning = `Causal cycle detected at event ${current.id}; chain is incomplete.`; break; }
    visited.add(current.id);
    chain.push(current);
    if (!current.causation_id) {
      if (!current.schema_version || current.schema_version < 2 || current.causation_id === undefined) warning = "Causal predecessor not recorded for legacy event; earlier history is unknown.";
      break;
    }
    const predecessor: RunEvent | undefined = byId.get(current.causation_id);
    if (!predecessor) warning = `Missing causal event: ${current.causation_id}; chain is incomplete.`;
    current = predecessor;
  }
  return { events: chain.reverse(), warning };
}

export function debugIdentity(value: RunEvent | import("./api").RunStep) {
  return { id: value.id, correlation_id: value.correlation_id ?? null, causation_id: value.causation_id ?? null, trace_id: value.trace_id ?? null, span_id: value.span_id ?? null, step_id: value.step_id ?? null };
}

type DiagnosisStep = { id: string; input: Record<string, unknown>; error: Record<string, unknown> | null };
export function diagnoseRun(run: { status: string }, events: RunEvent[], steps: DiagnosisStep[]) {
  if (!["failed", "cancelled", "interrupted"].includes(run.status)) return null;
  const outcome = mergeEvents([], events).findLast(event => event.type === `run.${run.status}`);
  const payload = outcome?.payload ?? {};
  // Only explicit identity links are causal evidence. A denied tool can recover;
  // the last failed step is not necessarily the cause of a terminal budget stop.
  const callMatches = typeof payload.call_id === "string" ? steps.filter(step => step.input.call_id === payload.call_id || events.some(event => event.payload.call_id === payload.call_id && event.payload.step_id === step.id)) : [];
  const explicitId = typeof payload.step_id === "string" ? payload.step_id : outcome?.step_id;
  const step = typeof explicitId === "string" ? steps.find(step => step.id === explicitId) : callMatches.length === 1 ? callMatches[0] : undefined;
  if (payload.retained === false && payload.reason === "retention_expired") return { title: `Run ${run.status}`, reason: "Data expired by retention; the original terminal reason is unavailable.", action: "Review retained event identities and metrics; removed historical content cannot be reconstructed.", stepId: step?.id ?? null };
  if (run.status === "cancelled") return { title: "Run cancelled", reason: "Execution was cancelled, not failed.", action: "Review committed partial output; start a new run if the task is still needed.", stepId: step?.id ?? null };
  if (run.status === "interrupted") return { title: "Run interrupted", reason: "Execution was interrupted before completion.", action: "Check runtime availability after restart; review committed partial output before starting a new run.", stepId: step?.id ?? null };
  const code = typeof payload.reason === "string" ? payload.reason : "";
  const [reason, action] = (Object.hasOwn(failureReasons, code) ? failureReasons[code] : undefined) ?? [code ? `Runtime reason: ${code}` : "The runtime failure reason was not recorded.", "Review the event timeline and safe step metadata before starting a new run."];
  const detail = step?.error?.message ?? step?.error?.reason ?? step?.error?.type;
  return { title: "Run failed", reason: reason + (code === "error" && typeof detail === "string" ? ` ${detail}` : ""), action, stepId: step?.id ?? null };
}

export function summarizeRun(run: { status: string; updated_at?: string }, events: RunEvent[], steps: { id: string; kind: string; status: string }[]) {
  const ordered = mergeEvents([], events);
  const start = Date.parse(ordered.find(event => event.type === "run.started")?.created_at ?? "");
  const finished = ["completed", "failed", "cancelled", "interrupted"].includes(run.status);
  const end = Date.parse(ordered.findLast(event => event.type === `run.${run.status}`)?.created_at ?? run.updated_at ?? "");
  const duration_ms = finished && Number.isFinite(start) && Number.isFinite(end) && end >= start ? end - start : null;
  const outcomes = new Map(steps.filter(step => step.kind === "tool").map(step => [step.id, step.status]));
  for (const event of ordered) {
    if (!["tool.completed", "tool.denied", "tool.failed"].includes(event.type)) continue;
    const stepId = event.step_id ?? event.payload.step_id;
    const id = typeof stepId === "string" ? stepId : typeof event.payload.call_id === "string" ? `call:${event.payload.call_id}` : `event:${event.sequence}`;
    outcomes.set(id, event.type.slice(5));
  }
  const count = (status: string) => [...outcomes.values()].filter(value => value === status).length;
  const model = steps.filter(step => step.kind === "model" && step.status === "failed").length;
  const planner = steps.filter(step => step.kind === "planner" && step.status === "failed").length;
  const tool = count("failed");
  return { duration_ms, tools: { completed: count("completed"), denied: count("denied"), failed: tool }, failures: { model, planner, tool, total: model + planner + tool } };
}

const eventLabels: Record<string, string> = {
  "run.created": "Run queued", "run.started": "Run started", "run.completed": "Run completed", "run.failed": "Run failed", "run.cancelled": "Run cancelled", "run.interrupted": "Run interrupted", "run.paused": "Run waiting for approval", "run.resumed": "Run resumed", "run.budget_exceeded": "Run budget exceeded",
  "model.requested": "Model requested", "model.delta": "Model output received", "model.retry": "Model retry scheduled", "model.completed": "Model response completed", "model.failed": "Model request failed", "model.cancelled": "Model request cancelled", "model.interrupted": "Model request interrupted",
  "planner.started": "Planner started", "planner.decided": "Planner chose an action", "planner.failed": "Planner failed", "planner.cancelled": "Planner cancelled", "planner.interrupted": "Planner interrupted",
  "tool.requested": "Tool requested", "tool.policy": "Tool policy checked", "tool.started": "Tool started", "tool.completed": "Tool completed", "tool.denied": "Tool denied", "tool.failed": "Tool failed", "tool.cancelled": "Tool cancelled", "tool.interrupted": "Tool interrupted",
  "approval.requested": "Approval requested", "approval.resolved": "Approval resolved", "approval.cancelled": "Approval cancelled", "artifact.created": "Artifact recorded", "artifact.expired": "Artifact expired by retention",
};
export function describeEvent(event: RunEvent) {
  const payload = event.payload;
  if (dataExpired(payload)) return { label: Object.hasOwn(eventLabels, event.type) ? eventLabels[event.type] : event.type, detail: "Data expired by retention" };
  const fields = event.type.startsWith("model.") ? [payload.provider, payload.model, payload.reason]
    : event.type.startsWith("tool.") ? [payload.tool_name, payload.decision, payload.reason]
    : event.type.startsWith("planner.") ? [payload.action, payload.reason]
    : event.type.startsWith("approval.") ? [payload.tool_name, payload.status, payload.approved === true ? "approved" : payload.approved === false ? "rejected" : null]
    : event.type.startsWith("run.") ? [payload.reason]
    : event.type === "artifact.created" ? [payload.path] : [];
  return { label: Object.hasOwn(eventLabels, event.type) ? eventLabels[event.type] : event.type, detail: fields.filter((value): value is string => typeof value === "string" && value.length > 0).join(" · ") };
}
