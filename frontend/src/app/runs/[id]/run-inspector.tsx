"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE, getApi, postApi, type Run, type RunEvent, type RunStep } from "@/lib/api";

const terminal = new Set(["completed", "failed", "cancelled", "interrupted"]);
const eventTypes = [
  "run.created", "run.started", "run.completed", "run.failed", "run.cancelled", "run.interrupted",
  "model.requested", "model.completed", "model.failed", "model.cancelled", "model.interrupted",
  "planner.started", "planner.decided", "planner.failed", "planner.cancelled", "planner.interrupted",
];

function mergeEvents(current: RunEvent[], incoming: RunEvent[]): RunEvent[] {
  const bySequence = new Map(current.map((event) => [event.sequence, event]));
  for (const event of incoming) bySequence.set(event.sequence, event);
  return [...bySequence.values()].sort((a, b) => a.sequence - b.sequence);
}

export function RunInspector({ initialRun, initialEvents, initialSteps }: {
  initialRun: Run;
  initialEvents: RunEvent[];
  initialSteps: RunStep[];
}) {
  const [run, setRun] = useState(initialRun);
  const [events, setEvents] = useState(() => mergeEvents([], initialEvents));
  const [steps, setSteps] = useState(initialSteps);
  const [connection, setConnection] = useState("connecting");
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [retry, setRetry] = useState(0);
  const cursor = useRef(Math.max(0, ...initialEvents.map((event) => event.sequence)));
  const finished = terminal.has(run.status);

  const refresh = useCallback(async (includeEvents = false) => {
    const [nextRun, nextSteps, nextEvents] = await Promise.all([
      getApi<Run>(`/runs/${initialRun.id}`),
      getApi<RunStep[]>(`/runs/${initialRun.id}/steps`),
      includeEvents ? getApi<RunEvent[]>(`/runs/${initialRun.id}/events`) : Promise.resolve(null),
    ]);
    setRun((previous) => {
      if (terminal.has(previous.status) && !terminal.has(nextRun.status)) return previous;
      if (previous.status === "running" && nextRun.status === "queued") return previous;
      return nextRun;
    });
    setSteps(nextSteps);
    if (nextEvents) {
      cursor.current = Math.max(cursor.current, ...nextEvents.map((event) => event.sequence));
      setEvents((previous) => mergeEvents(previous, nextEvents));
    }
    return nextRun;
  }, [initialRun.id]);

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
      void refresh(true).catch((cause) => {
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
        void refresh(event.type.startsWith("run.") && terminal.has(event.type.slice(4))).catch((cause) => {
          if (active) setError(cause instanceof Error ? cause.message : "Could not refresh run");
        });
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Invalid stream event");
      }
    };
    // The API sends named SSE events, not the default `message` event.
    for (const type of eventTypes) stream.addEventListener(type, onEvent);
    stream.onerror = () => {
      if (!active) return;
      setConnection("reconnecting");
      // Also check for a terminal state when the server has closed the stream.
      void refresh(true).catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : "Could not refresh run");
      });
    };
    return () => { active = false; stream.close(); };
  }, [initialRun.id, finished, refresh, retry]);

  async function start() {
    setStarting(true);
    setError("");
    try {
      const accepted = await postApi<Run>(`/runs/${run.id}/start`, {});
      setRun(accepted);
      await refresh(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start run");
    } finally {
      setStarting(false);
    }
  }

  async function cancel() {
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
      setCancelling(false);
    }
  }

  const result = events.findLast((event) => event.type === "run.completed")?.payload.result;

  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div><Link href="/runs" className="text-sm text-blue-700 hover:underline">← All runs</Link><h1 className="mt-2 text-3xl font-semibold tracking-tight">Run details</h1><p className="mt-2 break-all font-mono text-xs text-slate-500">{run.id} · version {run.agent_version_id}</p></div>
        <div className="flex flex-wrap items-center gap-3"><span role="status" className="rounded-full bg-slate-100 px-3 py-1 text-sm capitalize">{run.status.replaceAll("_", " ")}</span>{run.status === "queued" && <Button onClick={start} disabled={starting || cancelling}>{starting ? "Starting…" : "Start fake run"}</Button>}{!finished && <Button variant="destructive" onClick={cancel} disabled={starting || cancelling}>{cancelling ? "Cancelling…" : "Cancel run"}</Button>}</div>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600"><span role="status" aria-live="polite">{finished ? "Historical trace · run finished" : connection === "connected" ? "Live stream connected" : connection === "reconnecting" ? "Stream disconnected — reconnecting" : "Connecting to live stream…"}</span>{!finished && connection === "reconnecting" && <Button variant="outline" size="sm" onClick={() => setRetry((value) => value + 1)}>Retry now</Button>}</div>
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <Card><CardHeader><CardTitle>Input &amp; result</CardTitle></CardHeader><CardContent className="space-y-4"><p className="whitespace-pre-wrap break-words">{run.input}</p><div className="border-t pt-4"><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Result</p><p className="whitespace-pre-wrap break-words">{typeof result === "string" ? result : finished ? "No result recorded" : "Waiting for result…"}</p></div></CardContent></Card>
      <section aria-label="Steps"><h2 className="mb-3 text-lg font-semibold">Steps</h2><div className="space-y-3">{steps.length ? steps.map((step) => <Card key={step.id}><CardContent><details className="group"><summary className="cursor-pointer py-1 text-sm font-medium focus-visible:outline-2 focus-visible:outline-blue-500">#{step.sequence} {step.kind} · {step.status} <span className="text-xs font-normal text-slate-500">(show input, output and error)</span></summary><pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words border-t pt-3 text-xs text-slate-600">{JSON.stringify({ input: step.input, output: step.output, error: step.error }, null, 2)}</pre></details></CardContent></Card>) : <p className="text-sm text-slate-500">No steps recorded yet.</p>}</div></section>
      <section aria-label="Event timeline"><h2 className="mb-3 text-lg font-semibold">Event timeline</h2>{events.length ? <ol className="space-y-2">{events.map((event) => <li key={event.sequence} className="rounded-lg border bg-white p-3 text-sm"><span className="mr-2 font-mono text-xs text-slate-500">#{event.sequence}</span><span className="font-medium">{event.type}</span><details className="mt-2"><summary className="cursor-pointer text-xs text-blue-700 focus-visible:outline-2 focus-visible:outline-blue-500">Raw payload</summary><pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-xs text-slate-600">{JSON.stringify(event.payload, null, 2)}</pre></details></li>)}</ol> : <p className="text-sm text-slate-500">No events recorded yet.</p>}</section>
    </div>
  );
}
