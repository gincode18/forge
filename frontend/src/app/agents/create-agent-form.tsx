"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { postApi, type Agent, type Provider } from "@/lib/api";
import { ConfigFields, configFromForm } from "./config-fields";

const fieldClass = "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-blue-500";

export function CreateAgentForm({ providers }: { providers: Provider[] }) {
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
        ...configFromForm(data),
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
      <ConfigFields providers={providers} />
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <Button type="submit" disabled={pending}>{pending ? "Creating…" : "Create agent"}</Button>
    </form>
  );
}
