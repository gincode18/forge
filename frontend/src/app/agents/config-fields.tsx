"use client";

import { useId, useState } from "react";
import type { AgentVersion, Provider } from "@/lib/api";

const fieldClass = "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-blue-500";
const limits = [
  ["timeout_seconds", "Timeout (seconds)", 30, 0.001, undefined, "any"],
  ["max_steps", "Maximum steps", 12, 1, 100, "1"],
  ["max_output_tokens", "Output tokens / request", 2048, 1, undefined, "1"],
  ["max_retries", "Retries / request", 2, 0, 5, "1"],
  ["max_tokens", "Run token budget (optional)", null, 1, undefined, "1"],
  ["max_cost_usd", "Run cost budget, USD (optional)", null, 0.000001, undefined, "any"],
  ["input_cost_per_million", "Input USD / million tokens", null, 0, undefined, "any"],
  ["output_cost_per_million", "Output USD / million tokens", null, 0, undefined, "any"],
] as const;

export function configFromForm(data: FormData) {
  const values: Record<string, string | number | null> = {
    instructions: String(data.get("instructions") ?? "").trim(),
    provider: String(data.get("provider") ?? "fake").trim(),
    model: String(data.get("model") ?? "deterministic").trim(),
  };
  for (const [key] of limits) {
    const value = String(data.get(key) ?? "").trim();
    values[key] = value ? Number(value) : null;
  }
  if (values.max_cost_usd !== null && (values.input_cost_per_million === null || values.output_cost_per_million === null)) {
    throw new Error("A cost budget requires both explicit pricing rates. Forge does not assume vendor pricing.");
  }
  return values;
}

export function ConfigFields({ providers, initial }: { providers: Provider[]; initial?: AgentVersion }) {
  const id = useId();
  const [provider, setProvider] = useState(initial?.provider ?? "fake");
  const [model, setModel] = useState(initial?.model ?? "deterministic");
  const catalog = providers.find((item) => item.id === provider);
  return <div className="space-y-4">
    <div><label htmlFor={`${id}-instructions`} className="mb-1 block text-sm font-medium">Instructions</label><textarea id={`${id}-instructions`} name="instructions" required rows={4} defaultValue={initial?.instructions} className={fieldClass} /></div>
    <div><label htmlFor={`${id}-provider`} className="mb-1 block text-sm font-medium">Provider</label><input id={`${id}-provider`} list={`${id}-providers`} name="provider" required maxLength={80} value={provider} onChange={(event) => { const next = event.target.value; setProvider(next); const known = providers.find((item) => item.id === next); if (known) setModel(known.default_model); }} className={fieldClass} /><datalist id={`${id}-providers`}>{providers.map((item) => <option key={item.id} value={item.id} />)}</datalist></div>
    <div><label htmlFor={`${id}-model`} className="mb-1 block text-sm font-medium">Model</label><input id={`${id}-model`} name="model" required maxLength={160} value={model} onChange={(event) => setModel(event.target.value)} className={fieldClass} /></div>
    <p className="text-xs text-slate-500" role="status">{catalog ? `${provider}: ${catalog.configured ? "configured" : "not configured"}` : providers.length ? "Custom provider — availability checked by the runtime." : "Provider catalog unavailable — configuration status unknown."} Fake runs offline by default. Gemini requires GEMINI_API_KEY on the backend; keys are never entered here. Custom model text is allowed; no model discovery is performed.</p>
    <fieldset className="rounded-lg border p-3"><legend className="px-1 text-sm font-medium">Immutable run limits</legend><div className="grid gap-3 sm:grid-cols-2">{limits.map(([key, label, fallback, min, max, step]) => <div key={key}><label htmlFor={`${id}-${key}`} className="mb-1 block text-xs font-medium">{label}</label><input id={`${id}-${key}`} name={key} type="number" min={min} max={max} step={step} required={fallback !== null} defaultValue={initial ? initial[key] ?? "" : fallback ?? ""} className={fieldClass} /></div>)}</div><p className="mt-3 text-xs text-slate-500">Blank budgets are unlimited. Blank pricing means cost is unknown, not zero. Enter your own rates to enforce a cost budget. Each version keeps its own limits.</p></fieldset>
  </div>;
}
