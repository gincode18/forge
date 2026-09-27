"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { postApi, type Run } from "@/lib/api";

export function LaunchRunForm({ agentId, agentName }: { agentId: string; agentName: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [queuedId, setQueuedId] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = String(new FormData(event.currentTarget).get("input") ?? "").trim();
    if (!input || pending || queuedId) return;
    setPending(true);
    setError("");
    try {
      const queued = await postApi<Run>("/runs", { agent_id: agentId, input });
      setQueuedId(queued.id);
      await postApi<Run>(`/runs/${queued.id}/start`, {});
      router.push(`/runs/${queued.id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not launch run.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3 border-t pt-4">
      <label htmlFor={`launch-input-${agentId}`} className="block text-sm font-medium text-slate-900">Run {agentName}</label>
      <textarea id={`launch-input-${agentId}`} name="input" required rows={2} disabled={pending || !!queuedId} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50" placeholder="Enter an input for this agent" />
      {error && <p role="alert" className="text-sm text-red-700">{error}{queuedId && <> The run was queued; <Link className="underline" href={`/runs/${queuedId}`}>open it to retry starting</Link>.</>}</p>}
      <Button type="submit" disabled={pending || !!queuedId}>{pending ? "Launching…" : queuedId ? "Run queued" : "Launch fake run"}</Button>
    </form>
  );
}
