import Link from "next/link";
import { Shell } from "@/components/shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getApi, type Tool } from "@/lib/api";

export default async function ToolsPage() {
  let tools: Tool[] | null = null;
  try { tools = await getApi<Tool[]>("/tools"); } catch { /* Explicit unavailable state below. */ }
  return <Shell>
    <div className="mb-8"><h1 className="text-3xl font-semibold tracking-tight">Tools</h1><p className="mt-2 text-slate-600">Read-only catalog of versioned capabilities, schemas, and risks; tools cannot be enabled or invoked here. Enabling a tool permits requests, not guaranteed invocation. Enable exact tokens in a new <Link href="/agents" className="text-blue-700 underline">agent version</Link>.</p></div>
    <div role="note" className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><p className="font-semibold">Local controls are not a sandbox or security boundary.</p><p className="mt-1">Paths are relative to a per-run workspace. Sensitive writes and subprocess calls require approval. Subprocess commands must match the operator’s exact allowlist (empty by default). Review arguments before approving; only run agents you trust.</p></div>
    {tools === null ? <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-700">Cannot load tool catalog. Check that the Forge API is running, then <Link href="/tools" prefetch={false} className="underline">reload the catalog</Link>.</p> : tools.length === 0 ? <p className="text-slate-500">No tools available.</p> : <section aria-label="Tool catalog" className="grid items-start gap-4 md:grid-cols-2">{tools.map((tool) => <Card key={tool.key}>
      <CardHeader><CardTitle className="break-all font-mono text-lg">{tool.key}</CardTitle></CardHeader>
      <CardContent className="space-y-4 text-sm"><p>{tool.description}</p><dl className="grid grid-cols-2 gap-2"><dt className="text-slate-500">Risk</dt><dd className="font-medium capitalize">{tool.risk}</dd><dt className="text-slate-500">Default policy</dt><dd>{tool.default_policy.replaceAll("_", " ")}</dd><dt className="text-slate-500">Capabilities</dt><dd className="break-words">{tool.capabilities.join(", ") || "None"}</dd><dt className="text-slate-500">Timeout</dt><dd>{tool.timeout_seconds} seconds</dd><dt className="text-slate-500">Output limit</dt><dd>{tool.max_output_bytes.toLocaleString()} bytes</dd></dl>
        {tool.security_warning && <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">{tool.security_warning}</p>}
        {[["Input schema", tool.input_schema], ["Output schema", tool.output_schema]].map(([label, schema]) => <details key={String(label)} className="border-t pt-3"><summary className="cursor-pointer text-blue-700 focus-visible:outline-2 focus-visible:outline-blue-500">{String(label)}</summary><pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words text-xs text-slate-600">{JSON.stringify(schema, null, 2)}</pre></details>)}
      </CardContent>
    </Card>)}</section>}
  </Shell>;
}
