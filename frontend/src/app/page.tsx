import Link from "next/link";
import { ArrowUpRight, Activity, Database } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Shell } from "@/components/shell";
import { getApi, type Health } from "@/lib/api";

export default async function Home() {
  let health: Health | null = null;
  try {
    health = await getApi<Health>("/health");
  } catch {
    // The dashboard remains useful while the local API is stopped.
  }

  return (
    <Shell>
      <section className="grid items-start gap-10 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="max-w-2xl">
          <p className="mb-4 text-sm font-semibold uppercase tracking-widest text-blue-700">Local agent workspace</p>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">Build agents you can inspect, control, and trust.</h1>
          <p className="mt-5 text-lg leading-8 text-slate-600">Create immutable agent versions, launch deterministic fake runs, and inspect their persisted traces. Real models and tools are not available yet.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/agents" className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">View agents <ArrowUpRight className="size-4" aria-hidden="true" /></Link>
            <Link href="/runs" className="inline-flex items-center rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium hover:bg-slate-50">View runs</Link>
          </div>
        </div>
        <Card className="bg-slate-950 text-white ring-slate-800">
          <CardHeader><CardTitle className="flex items-center gap-2"><Activity className="size-4" aria-hidden="true" /> Service status</CardTitle></CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="flex justify-between gap-4"><span className="text-slate-400">API service</span><span className={health ? "text-emerald-300" : "text-amber-300"}>{health ? `Connected · v${health.version}` : "Unavailable"}</span></div>
            <div className="flex justify-between gap-4"><span className="flex items-center gap-2 text-slate-400"><Database className="size-4" aria-hidden="true" /> Storage</span><span>{health ? "SQLite ready" : "Unknown"}</span></div>
            {!health && <p className="border-t border-slate-800 pt-4 text-slate-400">Start the backend API on port 8000 to view persisted data.</p>}
          </CardContent>
        </Card>
      </section>
    </Shell>
  );
}