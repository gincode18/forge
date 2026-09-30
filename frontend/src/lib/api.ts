export const API_BASE = process.env.NEXT_PUBLIC_FORGE_API_URL ?? "http://localhost:8000";

export type Health = { status: "ok"; database: "ready"; version: string };
export type Provider = { id: string; configured: boolean; default_model: string };
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
};
export type RunEvent = {
  id: string;
  sequence: number;
  type: string;
  payload: Record<string, unknown>;
};
export type RunStep = {
  id: string;
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
