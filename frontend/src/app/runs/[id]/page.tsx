import { Shell } from "@/components/shell";
import { getApi, type Run, type RunEvent, type RunStep } from "@/lib/api";
import { RunInspector } from "./run-inspector";

export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let data: [Run, RunEvent[], RunStep[]] | null = null;
  try {
    data = await Promise.all([
      getApi<Run>(`/runs/${id}`),
      getApi<RunEvent[]>(`/runs/${id}/events`),
      getApi<RunStep[]>(`/runs/${id}/steps`),
    ]);
  } catch {
    // Render an explicit unavailable state below.
  }
  if (!data) return <Shell><p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-amber-900">Run unavailable. Check the run ID and that the Forge API is running.</p></Shell>;
  const [run, events, steps] = data;
  return <Shell><RunInspector initialRun={run} initialEvents={events} initialSteps={steps} /></Shell>;
}
