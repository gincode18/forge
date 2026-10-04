"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { postApi, type Agent, type Run } from "@/lib/api";

export function QueueRunForm({ agents }: { agents: Agent[] }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setPending(true);
    setError("");
    try {
      const run = await postApi<Run>("/runs", {
        agent_id: String(data.get("agent_id")),
        input: String(data.get("input") ?? "").trim(),
      });
      form.reset();
      router.push(`/runs/${run.id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not queue run.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div><label htmlFor="run-agent" className="mb-1 block text-sm font-medium">Agent</label><select id="run-agent" name="agent_id" required disabled={!agents.length} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-blue-500"><option value="">Choose an agent</option>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name} · v{agent.latest_version.version}</option>)}</select></div>
      <div><label htmlFor="run-input" className="mb-1 block text-sm font-medium">Run task / input</label><textarea id="run-input" name="input" aria-describedby="queue-run-help" required rows={3} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-blue-500" placeholder="What should this run do?" /></div>
      <p id="queue-run-help" className="text-xs text-slate-500">Queue run creates a record pinned to the latest saved agent version; it does not start execution. Review the run, then choose Start run on its detail page. For immediate execution, use Launch run on the Agents page. This input is the task for one run, not the agent’s reusable instructions. Fake is a deterministic test simulator, not a natural-language intelligent model; it echoes input or follows explicit forge_script JSON.</p>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <Button type="submit" disabled={pending || !agents.length}>{pending ? "Queuing…" : "Queue run"}</Button>
    </form>
  );
}
