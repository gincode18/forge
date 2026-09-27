import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Shell } from "@/components/shell";
import { getApi, type Agent, type Run } from "@/lib/api";
import { QueueRunForm } from "./queue-run-form";

export default async function RunsPage() {
  let agents: Agent[] = [];
  let runs: Run[] = [];
  let unavailable = false;
  try {
    [agents, runs] = await Promise.all([getApi<Agent[]>("/agents"), getApi<Run[]>("/runs")]);
  } catch {
    unavailable = true;
  }
  const agentNames = new Map(agents.map((agent) => [agent.latest_version.id, agent.name]));

  return (
    <Shell>
      <div className="mb-8"><h1 className="text-3xl font-semibold tracking-tight">Runs</h1><p className="mt-2 text-slate-600">Persisted requests and their deterministic fake-agent traces.</p></div>
      <div className="grid items-start gap-8 lg:grid-cols-[1fr_360px]">
        <section aria-label="Saved runs" className="space-y-3">
          {unavailable ? <p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-amber-900">Cannot load runs. Check that the Forge API is running.</p> :
            runs.length === 0 ? <p className="rounded-xl border border-dashed p-8 text-slate-600">No runs yet. Queue a request to create the first record.</p> :
              runs.map((run) => <Card key={run.id}><CardHeader><CardTitle className="flex flex-wrap items-center justify-between gap-2"><Link href={`/runs/${run.id}`} className="truncate text-blue-700 hover:underline">{agentNames.get(run.agent_version_id) ?? "Agent version"}</Link><span className="rounded-full bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800">{run.status}</span></CardTitle></CardHeader><CardContent className="space-y-2"><p className="break-words">{run.input}</p><p className="break-all font-mono text-xs text-slate-500">{run.id} · version {run.agent_version_id}</p></CardContent></Card>) }
        </section>
        <Card><CardHeader><CardTitle>Queue a run</CardTitle></CardHeader><CardContent>{!agents.length && !unavailable && <p className="mb-4 text-sm text-slate-600">Create an <Link href="/agents" className="underline">agent</Link> first.</p>}<QueueRunForm agents={agents} /></CardContent></Card>
      </div>
    </Shell>
  );
}
