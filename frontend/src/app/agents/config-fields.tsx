"use client";

import { useEffect, useId, useState } from "react";
import Link from "next/link";
import { getApi, type AgentVersion, type Provider, type Tool } from "@/lib/api";
import { limits } from "@/lib/agent-config";
export { configFromForm } from "@/lib/agent-config";

const fieldClass = "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-blue-500";
export function ConfigFields({ providers, initial, onToolsReady }: { providers: Provider[]; initial?: AgentVersion; onToolsReady: (ready: boolean) => void }) {
  const id = useId();
  const [provider, setProvider] = useState(initial?.provider ?? "fake");
  const [model, setModel] = useState(initial?.model ?? "deterministic");
  const [tools, setTools] = useState<Tool[] | null>(null);
  const [toolsError, setToolsError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    getApi<Tool[]>("/tools").then((catalog) => {
      if (active) { setTools(catalog); setToolsError(""); onToolsReady(true); }
    }).catch((cause) => {
      if (active) { setToolsError(cause instanceof Error ? cause.message : "Could not load tools"); onToolsReady(false); }
    });
    return () => { active = false; };
  }, [retry, onToolsReady]);
  const catalog = providers.find((item) => item.id === provider);
  return <div className="space-y-4">
    <div><label htmlFor={`${id}-instructions`} className="mb-1 block text-sm font-medium">Instructions</label><textarea id={`${id}-instructions`} name="instructions" required rows={4} defaultValue={initial?.instructions} className={fieldClass} /></div>
    <div><label htmlFor={`${id}-provider`} className="mb-1 block text-sm font-medium">Provider</label><input id={`${id}-provider`} list={`${id}-providers`} name="provider" required maxLength={80} value={provider} onChange={(event) => { const next = event.target.value; setProvider(next); const known = providers.find((item) => item.id === next); if (known) setModel(known.default_model); }} className={fieldClass} /><datalist id={`${id}-providers`}>{providers.map((item) => <option key={item.id} value={item.id} />)}</datalist></div>
    <div><label htmlFor={`${id}-model`} className="mb-1 block text-sm font-medium">Model</label><input id={`${id}-model`} name="model" required maxLength={160} value={model} onChange={(event) => setModel(event.target.value)} className={fieldClass} /></div>
    <p className="text-xs text-slate-500" role="status">{catalog ? `${provider}: ${catalog.configured ? "configured" : "not configured"}` : providers.length ? "Custom provider — availability checked by the runtime." : "Provider catalog unavailable — configuration status unknown."} Fake runs offline by default. Gemini requires GEMINI_API_KEY on the backend; keys are never entered here. Custom model text is allowed; no model discovery is performed.</p>
    <fieldset className="space-y-3 rounded-lg border p-3" aria-busy={tools === null && !toolsError}><legend className="px-1 text-sm font-medium">Enabled tools · immutable version</legend>
      <p id={`${id}-tools-help`} className="text-xs text-slate-600">Local controls are not a sandbox or security boundary. Sensitive tools require approval. Changes apply only to the new version. <Link href="/tools" className="text-blue-700 underline">Review schemas and risks</Link></p>
      {toolsError ? <div><p role="alert" className="text-sm text-red-700">{toolsError}. Saving is disabled until the tool catalog loads.</p><button type="button" onClick={() => { setToolsError(""); setRetry((value) => value + 1); }} className="mt-2 text-sm text-blue-700 underline focus-visible:outline-2">Retry tool catalog</button></div> : tools === null ? <p role="status" className="text-sm text-slate-500">Loading tool catalog…</p> : tools.length === 0 ? <p className="text-sm text-slate-500">No tools available.</p> : tools.map((tool) => <label key={tool.key} className="flex items-start gap-3 rounded-md border p-2 text-sm"><input type="checkbox" name="tools" value={tool.key} defaultChecked={initial?.tools.includes(tool.key)} aria-describedby={`${id}-tools-help`} className="mt-1 size-4 accent-blue-600 focus-visible:outline-2 focus-visible:outline-blue-500" /><span><span className="font-mono font-medium">{tool.key}</span><span className="block text-xs text-slate-500">{tool.description} · {tool.risk} risk · {tool.default_policy.replaceAll("_", " ")}</span></span></label>)}
      {tools && initial?.tools.filter((key) => !tools.some((tool) => tool.key === key)).map((key) => <label key={key} className="flex gap-3 text-sm text-amber-900"><input type="checkbox" name="tools" value={key} defaultChecked /><span>{key} — unavailable; cannot execute. Uncheck to remove from the new version.</span></label>)}
    </fieldset>
    <fieldset className="rounded-lg border p-3"><legend className="px-1 text-sm font-medium">Immutable run limits</legend><div className="grid gap-3 sm:grid-cols-2">{limits.map(([key, label, fallback, min, max, step]) => <div key={key}><label htmlFor={`${id}-${key}`} className="mb-1 block text-xs font-medium">{label}</label><input id={`${id}-${key}`} name={key} type="number" min={min} max={max} step={step} required={fallback !== null} defaultValue={initial ? initial[key] ?? "" : fallback ?? ""} className={fieldClass} /></div>)}</div><p className="mt-3 text-xs text-slate-500">Blank budgets are unlimited. Blank pricing means cost is unknown, not zero. Enter your own rates to enforce a cost budget. Each version keeps its own limits.</p></fieldset>
  </div>;
}
