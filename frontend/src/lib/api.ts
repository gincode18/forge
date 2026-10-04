export const API_BASE = process.env.NEXT_PUBLIC_FORGE_API_URL ?? "http://localhost:8000";

export type Health = { status: "ok"; database: "ready"; version: string };
export type Provider = { id: string; configured: boolean; default_model: string };
export type Tool = {
  name: string; version: string; key: string; description: string;
  input_schema: Record<string, unknown>; output_schema: Record<string, unknown>;
  capabilities: string[]; risk: "low" | "sensitive"; timeout_seconds: number;
  max_output_bytes: number; default_policy: "allow" | "require_approval"; security_warning: string;
};
export type Approval = {
  id: string; run_id: string; step_id: string;
  tool_name: string; tool_version: string; arguments: Record<string, unknown>;
  status: "pending" | "approved" | "rejected" | "cancelled";
  created_at: string; resolved_at: string | null;
};
export type Artifact = {
  id: string; run_id: string; path: string; size_bytes: number;
  media_type: string; created_at: string; expired?: boolean;
};

export function artifactDownloadUrl(runId: string, artifactId: string): string {
  return `${API_BASE}/api/v1/runs/${encodeURIComponent(runId)}/artifacts/${encodeURIComponent(artifactId)}`;
}

export type AgentVersion = {
  id: string; version: number; instructions: string; provider: string; model: string;
  planner: string; tools: string[]; max_steps: number; timeout_seconds: number;
  max_tokens: number | null; max_cost_usd: number | null; max_retries: number;
  max_output_tokens: number; input_cost_per_million: number | null; output_cost_per_million: number | null;
};
export type Agent = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  latest_version: AgentVersion;
};
export type Run = {
  id: string;
  agent_version_id: string;
  input: string;
  status: string;
  created_at: string;
  updated_at?: string;
};
export type TraceIdentity = {
  correlation_id?: string | null;
  causation_id?: string | null;
  trace_id?: string | null;
  span_id?: string | null;
  step_id?: string | null;
};
export type RunEvent = TraceIdentity & {
  id: string;
  run_id?: string;
  created_at?: string;
  schema_version?: number;
  sequence: number;
  type: string;
  payload: Record<string, unknown>;
};
export type RunStep = TraceIdentity & {
  id: string;
  run_id?: string;
  created_at?: string;
  started_at?: string | null;
  finished_at?: string | null;
  sequence: number;
  attempt: number;
  kind: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error: Record<string, unknown> | null;
};

export async function getApi<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Forge API returned ${response.status}`);
  return response.json() as Promise<T>;
}

export async function postApi<T>(path: string, body: object): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error: { detail?: string | { msg: string }[] } = await response.json();
    const detail = error.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.map((item) => item.msg).join("; ") || `Forge API returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}
