"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { postApi, type Agent } from "@/lib/api";

const fieldClass = "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-blue-500";

export function CreateAgentForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      await postApi<Agent>("/agents", {
        name: String(data.get("name") ?? "").trim(),
        description: String(data.get("description") ?? "").trim() || null,
        instructions: String(data.get("instructions") ?? "").trim(),
      });
      form.reset();
      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not create agent.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div><label htmlFor="agent-name" className="mb-1 block text-sm font-medium">Name</label><input id="agent-name" name="name" required maxLength={120} className={fieldClass} placeholder="Home Agent" /></div>
      <div><label htmlFor="agent-description" className="mb-1 block text-sm font-medium">Description</label><input id="agent-description" name="description" className={fieldClass} placeholder="What this agent is for" /></div>
      <div><label htmlFor="agent-instructions" className="mb-1 block text-sm font-medium">Instructions</label><textarea id="agent-instructions" name="instructions" required rows={4} className={fieldClass} placeholder="Explain what the agent should do" /></div>
      <p className="text-xs text-slate-500">Creates version 1 with the fake provider. No model execution is available yet.</p>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <Button type="submit" disabled={pending}>{pending ? "Creating…" : "Create agent"}</Button>
    </form>
  );
}
