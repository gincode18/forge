import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Shell } from "@/components/shell";
import { getApi, type Agent } from "@/lib/api";
import { CreateAgentForm } from "./create-agent-form";
import { LaunchRunForm } from "./launch-run-form";

export default async function AgentsPage() {
  let agents: Agent[] = [];
  let unavailable = false;
  try {
    agents = await getApi<Agent[]>("/agents");
  } catch {
    unavailable = true;
  }

  return (
    <Shell>
      <div className="mb-8"><h1 className="text-3xl font-semibold tracking-tight">Agents</h1><p className="mt-2 text-slate-600">Durable definitions and immutable configurations.</p></div>
      <div className="grid items-start gap-8 lg:grid-cols-[1fr_360px]">
        <section aria-label="Saved agents" className="space-y-3">
          {unavailable ? <p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-amber-900">Cannot load agents. Check that the Forge API is running.</p> :
            agents.length === 0 ? <p className="rounded-xl border border-dashed p-8 text-slate-600">No agents yet. Create one to get started.</p> :
              agents.map((agent) => (
                <Card key={agent.id}><CardHeader><CardTitle>{agent.name}</CardTitle></CardHeader><CardContent className="space-y-2 text-slate-600">
                  <p>{agent.description || "No description"}</p>
                  <p className="text-xs">Version {agent.latest_version.version} · {agent.latest_version.provider} / {agent.latest_version.model}</p>
                  <p className="break-all font-mono text-xs text-slate-500">{agent.id}</p>
                  <LaunchRunForm agentId={agent.id} agentName={agent.name} />
                </CardContent></Card>
              ))}
        </section>
        <Card><CardHeader><CardTitle>Create agent</CardTitle></CardHeader><CardContent><CreateAgentForm /></CardContent></Card>
      </div>
    </Shell>
  );
}
