"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE, artifactDownloadUrl, getApi, postApi, type Approval, type Artifact, type Run, type RunEvent, type RunStep } from "@/lib/api";
import { dataExpired, causalChain, debugIdentity, canResolveApproval, mergeEvents, streamedOutputs, modelMetrics, safeMetadata, runEventTypes, eventFilters, filterEvents, describeEvent, diagnoseRun, summarizeRun, type EventFilter } from "@/lib/run-trace";

const terminal = new Set(["completed", "failed", "cancelled", "interrupted"]);


export function RunInspector({ initialRun, initialEvents, initialSteps }: {
  initialRun: Run;
  initialEvents: RunEvent[];
  initialSteps: RunStep[];
}) {
  const [run, setRun] = useState(initialRun);
  const [events, setEvents] = useState(() => mergeEvents([], initialEvents));
  const [steps, setSteps] = useState(initialSteps);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [resolving, setResolving] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const commandInFlight = useRef(false);
  const manualRefreshInFlight = useRef(false);
  const [connection, setConnection] = useState("connecting");
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [retry, setRetry] = useState(0);
  const [eventFilter, setEventFilter] = useState<EventFilter>("All");
  const [eventLimit, setEventLimit] = useState(100);
  const [eventOffset, setEventOffset] = useState(0);
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null);
  const [chainOffset, setChainOffset] = useState(0);
  const eventJump = useRef<string | null>(null);
  const cursor = useRef(Math.max(0, ...initialEvents.map((event) => event.sequence)));
  const finished = terminal.has(run.status);
  const refreshIssued = useRef(0);
  const refreshApplied = useRef(0);

  const refresh = useCallback(async (includeEvents = false) => {
    const request = ++refreshIssued.current;
    const [nextRun, nextSteps, nextEvents, nextApprovals, nextArtifacts] = await Promise.all([
      getApi<Run>(`/runs/${initialRun.id}`),
      getApi<RunStep[]>(`/runs/${initialRun.id}/steps`),
      includeEvents ? getApi<RunEvent[]>(`/runs/${initialRun.id}/events`) : Promise.resolve(null),
      getApi<Approval[]>(`/runs/${initialRun.id}/approvals`),
      getApi<Artifact[]>(`/runs/${initialRun.id}/artifacts`),
    ]);
    if (request >= refreshApplied.current) {
      refreshApplied.current = request;
      setRun((previous) => {
        if (terminal.has(previous.status) && !terminal.has(nextRun.status)) return previous;
        if (previous.status === "running" && nextRun.status === "queued") return previous;
        return nextRun;
      });
      setSteps(nextSteps);
      setApprovals(nextApprovals);
      setArtifacts(nextArtifacts);
    }
    if (nextEvents) {
      cursor.current = Math.max(cursor.current, ...nextEvents.map((event) => event.sequence));
      setEvents((previous) => mergeEvents(previous, nextEvents));
    }
    return nextRun;
  }, [initialRun.id]);

  useEffect(() => {
    // Finished runs have no SSE connection, but still need durable controls.
    let active = true;
    void Promise.resolve().then(async () => { if (active) await refresh(true); }).catch((cause) => {
      if (active) setError(cause instanceof Error ? cause.message : "Could not refresh run");
    });
    return () => { active = false; };
  }, [refresh]);

  useEffect(() => {
    if (finished) return;
    let active = true;
    // The initial server snapshot can race with subscription. Replaying from its
    // last persisted sequence closes that gap; native EventSource reconnects use
    // the server's Last-Event-ID support. Merging by sequence tolerates overlap.
    const stream = new EventSource(`${API_BASE}/api/v1/runs/${initialRun.id}/stream?since=${cursor.current}`);
    stream.onopen = () => {
      if (!active) return;
      setConnection("connected");
      void refresh(true).then(() => { if (active) setError(""); }).catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : "Could not refresh run");
      });
    };
    const onEvent = (message: MessageEvent) => {
      if (!active) return;
      try {
        const event = JSON.parse(message.data) as RunEvent;
        if (typeof event.sequence !== "number" || !event.id || !event.type) throw new Error("Invalid event");
        cursor.current = Math.max(cursor.current, event.sequence);
        setEvents((previous) => mergeEvents(previous, [event]));
        if (event.type === "model.delta") return;
        void refresh(event.type.startsWith("run.") && terminal.has(event.type.slice(4))).catch((cause) => {
          if (active) setError(cause instanceof Error ? cause.message : "Could not refresh run");
        });
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Invalid stream event");
      }
    };
    // The API sends named SSE events, not the default `message` event.
    for (const type of runEventTypes) stream.addEventListener(type, onEvent);
    stream.onerror = () => {
      if (!active) return;
      setConnection("reconnecting");
      // Also check for a terminal state when the server has closed the stream.
      void refresh(true).then(() => { if (active) setError(""); }).catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : "Could not refresh run");
      });
    };
    return () => { active = false; stream.close(); };
  }, [initialRun.id, finished, refresh, retry]);

  useEffect(() => {
    if (!eventJump.current || typeof document === "undefined") return;
    const target = document.getElementById(`event-${encodeURIComponent(eventJump.current)}`);
    if (target) { target.scrollIntoView({ block: "center" }); target.focus(); eventJump.current = null; }
  }, [expandedEvent, eventFilter, eventOffset]);

  function revealEvent(id: string) {
    eventJump.current = id;
    setEventFilter("All");
    setEventOffset(0);
    setExpandedEvent(id);
  }

  async function start() {
    if (commandInFlight.current) return;
    commandInFlight.current = true;
    setStarting(true);
    setError("");
    try {
      const accepted = await postApi<Run>(`/runs/${run.id}/start`, {});
      setRun(accepted);
      await refresh(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start run");
    } finally {
      commandInFlight.current = false;
      setStarting(false);
    }
  }

  async function cancel() {
    if (commandInFlight.current) return;
    commandInFlight.current = true;
    setCancelling(true);
    setError("");
    try {
      const cancelled = await postApi<Run>(`/runs/${run.id}/cancel`, {});
      setRun(cancelled);
      await refresh(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not cancel run");
      // A conflicting cancellation may mean another client finished it first.
      try { await refresh(true); } catch { /* Retain the command error. */ }
    } finally {
      commandInFlight.current = false;
      setCancelling(false);
    }
  }

  async function resolveApproval(approval: Approval, approved: boolean) {
    if (!canResolveApproval(approval, run.status, commandInFlight.current)) return;
    commandInFlight.current = true;
    setResolving(approval.id);
    setError("");
    try {
      await postApi<Approval>(`/approvals/${approval.id}/resolve`, { approved });
      await refresh(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not resolve approval");
      // Includes 409: another client may have resolved or cancelled this call.
      try { await refresh(true); } catch { /* Retain the decision error. */ }
    } finally {
      commandInFlight.current = false;
      setResolving(null);
    }
  }

  async function refreshTrace() {
    if (manualRefreshInFlight.current) return;
    manualRefreshInFlight.current = true;
    setRefreshing(true);
    setError("");
    try { await refresh(true); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not refresh run"); }
    finally { manualRefreshInFlight.current = false; setRefreshing(false); }
  }

  const expiredModels = new Set([
    ...steps.filter(step => step.kind === "model" && dataExpired(step.output)).map(step => step.id),
    ...events.filter(event => event.type.startsWith("model.") && dataExpired(event.payload)).map(event => event.step_id ?? event.payload.step_id),
  ]);
  const displayEvents = events.map(event => event.type.startsWith("model.") && expiredModels.has(event.step_id ?? event.payload.step_id)
    ? { ...event, payload: { ...event.payload, text: { retained: false, reason: "retention_expired" } } } : event);
  const partialOutputs = streamedOutputs(displayEvents);
  const metrics = modelMetrics(steps);
  const retryCount = Math.max(metrics.retries, events.filter((event) => event.type === "model.retry").length);
  const diagnosis = diagnoseRun(run, events, steps);
  const diagnosedStep = steps.find(step => step.id === diagnosis?.stepId);
  const summary = summarizeRun(run, events, steps);
  const filteredEvents = filterEvents(displayEvents, eventFilter);
  const windowEnd = Math.max(0, filteredEvents.length - eventOffset);
  const windowStart = Math.max(0, windowEnd - eventLimit);
  const windowEvents = filteredEvents.slice(windowStart, windowEnd);
  const pinnedEvent = filteredEvents.find(event => event.id === expandedEvent);
  const visibleEvents = pinnedEvent && !windowEvents.some(event => event.id === pinnedEvent.id) ? mergeEvents(windowEvents, [pinnedEvent]) : windowEvents;
  const terminalEvent = events.findLast((event) => event.type === `run.${run.status}`);
  const chain = terminalEvent ? causalChain(events, terminalEvent.id) : null;
  const chainEnd = Math.max(0, (chain?.events.length ?? 0) - chainOffset);
  const chainStart = Math.max(0, chainEnd - 100);
  const visibleChain = chain?.events.slice(chainStart, chainEnd) ?? [];
  const result = events.findLast((event) => event.type === "run.completed")?.payload.result;

  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div><Link href="/runs" className="text-sm text-blue-700 hover:underline">← All runs</Link><h1 className="mt-2 text-3xl font-semibold tracking-tight">Run details</h1><p className="mt-2 break-all font-mono text-xs text-slate-500">{run.id} · version {run.agent_version_id}</p></div>
        <div className="flex flex-wrap items-center gap-3"><span role="status" className="rounded-full bg-slate-100 px-3 py-1 text-sm capitalize">{run.status.replaceAll("_", " ")}</span>{run.status === "queued" && <Button onClick={start} disabled={starting || cancelling || resolving !== null}>{starting ? "Starting…" : "Start run"}</Button>}{!finished && <Button variant="destructive" onClick={cancel} disabled={starting || cancelling || resolving !== null}>{cancelling ? "Cancelling…" : "Cancel run"}</Button>}</div>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600"><span role="status" aria-live="polite">{finished ? "Historical trace · run finished" : connection === "connected" ? "Live stream connected" : connection === "reconnecting" ? "Stream disconnected — reconnecting" : "Connecting to live stream…"}</span>{!finished && connection === "reconnecting" && <Button variant="outline" size="sm" onClick={() => setRetry((value) => value + 1)}>Retry now</Button>}<Button variant="outline" size="sm" onClick={refreshTrace} disabled={refreshing}>{refreshing ? "Refreshing…" : "Refresh trace"}</Button></div>
      {(events.some(event => dataExpired(event.payload)) || steps.some(step => dataExpired(step.input) || dataExpired(step.output) || dataExpired(step.error))) && <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">Data expired by retention. The historical trace is incomplete; retained IDs and metrics do not restore removed content.</p>}
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <section aria-label="Tool approvals" className="space-y-3">
        <h2 className="text-lg font-semibold">Tool approvals</h2>
        <p className="text-sm text-slate-600">Review the exact arguments before allowing a sensitive tool. Local controls are not a sandbox or security boundary.</p>
        {approvals.length ? approvals.map((approval) => <Card key={approval.id}><CardContent className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="break-all font-mono text-sm font-medium">{approval.tool_name}@{approval.tool_version}</h3><span className="text-sm capitalize">{approval.status}</span></div>
          <p className="break-all text-xs text-slate-500">Step {approval.step_id} · requested {approval.created_at}{approval.resolved_at && ` · resolved ${approval.resolved_at}`}</p>
          <pre aria-label="Approval arguments" className="overflow-x-auto whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 text-xs">{JSON.stringify(safeMetadata(approval.arguments), null, 2)}</pre>
          {approval.status === "pending" && <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => resolveApproval(approval, true)} disabled={!canResolveApproval(approval, run.status, starting || cancelling || resolving !== null)}>Approve</Button>
            <Button variant="destructive" onClick={() => resolveApproval(approval, false)} disabled={!canResolveApproval(approval, run.status, starting || cancelling || resolving !== null)}>Reject</Button>
            {resolving === approval.id && <span role="status" className="text-sm text-slate-500">Resolving…</span>}
          </div>}
        </CardContent></Card>) : <p className="text-sm text-slate-500">No approvals recorded.</p>}
      </section>
      <section aria-label="Artifacts" className="space-y-3">
        <h2 className="text-lg font-semibold">Artifacts</h2>
        <div aria-label="Run workspace" className="space-y-1 rounded-lg border bg-slate-50 p-3 text-xs text-slate-600">
          <p className="font-medium">Run workspace · <code className="break-all">{`workspaces/${run.id}`}</code></p>
          <p>Relative tool paths belong to this run under the operator’s FORGE_DATA_DIR (backend/data by default). Every run has a separate workspace; files are not automatically shared between runs.</p>
          <p>Recorded writes are listed below. This is not a full file browser, and a workspace is not a sandbox.</p>
        </div>
        {artifacts.length ? <ul className="space-y-2">{artifacts.map((artifact) => <li key={artifact.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-white p-3">
          <div className="min-w-0"><p className="break-all font-mono text-sm">{artifact.path}</p><p className="mt-1 text-xs text-slate-500">{artifact.size_bytes.toLocaleString()} bytes · {artifact.media_type} · {artifact.created_at}</p></div>
          {artifact.expired ? <span className="text-sm text-slate-500">Expired by retention</span> : <a href={artifactDownloadUrl(run.id, artifact.id)} download className="rounded text-sm font-medium text-blue-700 hover:underline focus-visible:outline-2 focus-visible:outline-blue-500" aria-label={`Download ${artifact.path}`}>Download</a>}
        </li>)}</ul> : <p className="text-sm text-slate-500">No artifacts recorded.</p>}
      </section>
      {diagnosis && <section aria-label="Run diagnosis" className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <h2 className="font-semibold">{diagnosis.title}</h2>
        <p>{diagnosis.reason}</p>
        {diagnosedStep && <p className="font-medium">{`Failed boundary: Step #${diagnosedStep.sequence} · ${diagnosedStep.kind}`}</p>}
        {diagnosis.stepId ? <a href={`#step-${encodeURIComponent(diagnosis.stepId)}`} className="inline-block text-blue-700 hover:underline focus-visible:outline-2 focus-visible:outline-blue-500">View exact linked step</a> : <p className="text-xs">No exact step linked by the runtime. A failed or denied step is not necessarily the cause.</p>}
        <p><span className="font-medium">Next action: </span>{diagnosis.action}</p>
        {terminalEvent && <details><summary className="cursor-pointer text-xs focus-visible:outline-2 focus-visible:outline-blue-500">Safe raw outcome</summary><pre className="mt-2 whitespace-pre-wrap break-words text-xs">{JSON.stringify(safeMetadata(terminalEvent.payload), null, 2)}</pre></details>}
        {chain && <div aria-label="Causal chain" className="space-y-2 border-t border-amber-200 pt-3">
          <h3 className="font-medium">Causal chain</h3>
          {chain.warning && <p role="status" className="text-xs">{chain.warning}</p>}
          <p className="text-xs">{`${visibleChain.length} shown of ${chain.events.length} causal events · predecessor order, not proof of fault`}</p>
          <div className="flex gap-2">
            {chainStart > 0 && <Button variant="outline" size="sm" onClick={() => setChainOffset(value => value + 100)}>Earlier causes</Button>}
            {chainOffset > 0 && <Button variant="outline" size="sm" onClick={() => setChainOffset(value => Math.max(0, value - 100))}>Later causes</Button>}
          </div>
          <ol className="space-y-2">{visibleChain.map(event => <li key={event.id}>
            <a href={`#event-${encodeURIComponent(event.id)}`} onClick={click => { click.preventDefault(); revealEvent(event.id); }} className="text-blue-700 hover:underline">#{event.sequence} {describeEvent(event).label}</a>
            {typeof (event.step_id ?? event.payload.step_id) === "string" && steps.some(step => step.id === (event.step_id ?? event.payload.step_id)) && <a href={`#step-${encodeURIComponent(String(event.step_id ?? event.payload.step_id))}`} className="ml-3 text-blue-700 hover:underline">Step boundary</a>}
          </li>)}</ol>
        </div>}
        <p className="text-xs">Committed steps and partial output remain available below.</p>
      </section>}
      <section aria-label="Run summary" className="space-y-2">
        <h2 className="text-lg font-semibold">Run summary</h2>
        <div className="grid gap-3 sm:grid-cols-4">{[
          ["Duration", summary.duration_ms === null ? "Unknown" : `${(summary.duration_ms / 1000).toLocaleString()} s`],
          ["Tools completed", String(summary.tools.completed)],
          ["Tools denied", String(summary.tools.denied)],
          ["Tools failed", String(summary.tools.failed)],
          ["Step failures", String(summary.failures.total)],
          ["Model failures", String(summary.failures.model)],
          ["Planner failures", String(summary.failures.planner)],
        ].map(([label, value]) => <Card key={label}><CardContent><p className="text-xs text-slate-500">{label}</p><p className="mt-1 font-mono text-lg">{value}</p></CardContent></Card>)}</div>
        <p className="text-xs text-slate-500">Duration covers execution from run start to terminal outcome, including approval waits, not queue time. Unknown until finished with valid timestamps. Denied tools are counted separately from failures.</p>
      </section>
      <section aria-label="Model metrics" className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">{[
        ["Model latency", metrics.latency_ms === null ? "Unknown" : `${metrics.latency_ms.toLocaleString()} ms`],
        ["Input tokens", metrics.input_tokens === null ? "Unknown" : metrics.input_tokens.toLocaleString()],
        ["Output / total tokens", `${metrics.output_tokens ?? "Unknown"} / ${metrics.total_tokens ?? "Unknown"}`],
        ["Estimated cost", metrics.cost_usd === null ? "Unknown" : `$${metrics.cost_usd.toFixed(6)}`],
        ["Retries", String(retryCount)],
      ].map(([label, value]) => <Card key={label}><CardContent><p className="text-xs text-slate-500">{label}</p><p className="mt-1 font-mono text-lg">{value}</p></CardContent></Card>)}</section>
      <Card><CardHeader><CardTitle>Input &amp; result</CardTitle></CardHeader><CardContent className="space-y-4"><p className="whitespace-pre-wrap break-words">{run.input}</p><div className="border-t pt-4"><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Result</p><p className="whitespace-pre-wrap break-words">{dataExpired(result) || dataExpired(terminalEvent?.payload) ? "Data expired by retention" : typeof result === "string" ? result : finished ? "No result recorded" : "Waiting for result…"}</p></div></CardContent></Card>
      {Object.keys(partialOutputs).length > 0 && <section aria-label="Committed model stream"><h2 className="mb-3 text-lg font-semibold">Committed model output</h2><div className="space-y-3">{Object.entries(partialOutputs).map(([id, text]) => <Card key={id}><CardContent><p className="mb-2 break-all font-mono text-xs text-slate-500">Step {id}</p><p className="whitespace-pre-wrap break-words text-sm">{steps.find((step) => step.id === id)?.output?.text as string || text || "Retry pending…"}</p></CardContent></Card>)}</div></section>}
      <section aria-label="Steps">
        <h2 className="mb-3 text-lg font-semibold">Steps</h2>
        <div className="space-y-3">{steps.length ? steps.map((step) => {
          const causal = step.id === diagnosis?.stepId;
          return <Card key={step.id} id={`step-${encodeURIComponent(step.id)}`} tabIndex={-1} className={causal ? "scroll-mt-4 border-amber-300 bg-amber-50" : "scroll-mt-4"}>
            <CardContent><details className="group" open={causal || undefined}>
              <summary className="cursor-pointer py-1 text-sm font-medium focus-visible:outline-2 focus-visible:outline-blue-500">#{step.sequence} {step.kind} · {step.status} <span className="text-xs font-normal text-slate-500">(show input, output and error)</span></summary>
              {step.kind === "model" && <div className="mt-3 space-y-2 border-t pt-3">
                <p className="text-xs text-slate-500">Attempt {step.attempt} · {String(step.output?.provider ?? step.input.provider ?? "Unknown provider")} / {String(step.output?.model ?? step.input.model ?? "Unknown model")} · finish: {String(step.output?.finish_reason ?? "Unknown")}</p>
                <p className="whitespace-pre-wrap break-words text-sm">{expiredModels.has(step.id) ? "Data expired by retention" : typeof step.output?.text === "string" ? step.output.text : partialOutputs[step.id] || "No model output recorded"}</p>
                <pre className="whitespace-pre-wrap break-words text-xs">{JSON.stringify(safeMetadata({ usage: step.output?.usage, latency_ms: step.output?.latency_ms, cost_usd: step.output?.cost_usd ?? "unknown", request_id: step.output?.request_id }), null, 2)}</pre>
              </div>}
              {(dataExpired(step.input) || dataExpired(step.output) || dataExpired(step.error)) && <p className="mt-2 text-xs text-amber-800">Data expired by retention</p>}
              <details className="mt-3" open={causal || undefined}><summary className="cursor-pointer text-xs text-blue-700">Normalized / safe raw metadata</summary><pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words border-t pt-3 text-xs text-slate-600">{JSON.stringify(safeMetadata({ ...debugIdentity(step), started_at: step.started_at ?? null, finished_at: step.finished_at ?? null, input: step.input, output: step.output, error: step.error }), null, 2)}</pre></details>
            </details></CardContent>
          </Card>;
        }) : <p className="text-sm text-slate-500">No steps recorded yet.</p>}</div>
      </section>
      <section aria-label="Event timeline" className="space-y-3">
        <h2 className="text-lg font-semibold">Event timeline</h2>
        <div role="group" aria-label="Filter events" className="flex flex-wrap gap-2">
          {eventFilters.map(filter => <Button key={filter} variant={eventFilter === filter ? "default" : "outline"} size="sm" aria-pressed={eventFilter === filter} onClick={() => { setEventFilter(filter); setEventLimit(100); setEventOffset(0); }}>{filter}</Button>)}
        </div>
        <p role="status" className="text-xs text-slate-500">{`${visibleEvents.length} shown of ${filteredEvents.length} ${eventFilter} events · ${events.length} total · sequence order`}</p>
        <p className="text-xs text-slate-500">Latest 100 initially; up to 500 per page. Filters reset to latest; refresh preserves the window.</p>
        <div className="flex flex-wrap gap-2">
          {windowStart > 0 && eventLimit < 500 && <Button variant="outline" size="sm" onClick={() => setEventLimit(value => Math.min(500, value + 100))}>Show earlier 100</Button>}
          {windowStart > 0 && eventLimit === 500 && <Button variant="outline" size="sm" onClick={() => setEventOffset(value => value + 500)}>Earlier page</Button>}
          {eventOffset > 0 && <Button variant="outline" size="sm" onClick={() => setEventOffset(value => Math.max(0, value - 500))}>Newer page</Button>}
          {(eventOffset > 0 || eventLimit > 100) && <Button variant="outline" size="sm" onClick={() => { setEventOffset(0); setEventLimit(100); }}>Latest 100</Button>}
        </div>
        {visibleEvents.length ? <ol className="space-y-2">{visibleEvents.map(event => {
          const description = describeEvent(event);
          return <li key={event.sequence} id={`event-${encodeURIComponent(event.id)}`} tabIndex={-1} className="scroll-mt-4 rounded-lg border bg-white p-3 text-sm">
            <span className="mr-2 font-mono text-xs text-slate-500">#{event.sequence}</span><span className="font-medium">{description.label}</span>
            <p className="mt-1 text-xs text-slate-500">{event.type} · {event.created_at ? <time dateTime={event.created_at}>{event.created_at}</time> : "Timestamp unknown"}</p>
            {description.detail && <p className="mt-2 whitespace-pre-wrap break-words text-sm">{description.detail}</p>}
            {typeof (event.step_id ?? event.payload.step_id) === "string" && steps.some(step => step.id === (event.step_id ?? event.payload.step_id)) && <a href={`#step-${encodeURIComponent(String(event.step_id ?? event.payload.step_id))}`} className="mt-2 inline-block text-xs text-blue-700 hover:underline">View linked step</a>}
            <details className="mt-2" open={event.id === expandedEvent} onToggle={toggle => { if (toggle.currentTarget.open) setExpandedEvent(event.id); else setExpandedEvent(previous => previous === event.id ? null : previous); }}><summary className="cursor-pointer text-xs text-blue-700 focus-visible:outline-2 focus-visible:outline-blue-500">Safe raw payload</summary><pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-xs text-slate-600">{JSON.stringify(safeMetadata({ ...debugIdentity(event), schema_version: event.schema_version ?? 1, payload: event.payload }), null, 2)}</pre></details>
          </li>;
        })}</ol> : <p className="text-sm text-slate-500">{eventFilter === "All" ? "No events recorded yet." : `No ${eventFilter.toLowerCase()} events recorded.`}</p>}
      </section>
    </div>
  );
}
