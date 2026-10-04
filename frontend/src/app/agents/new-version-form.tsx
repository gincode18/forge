"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { postApi, type Agent, type Provider } from "@/lib/api";
import { ConfigFields, configFromForm } from "./config-fields";

export function NewVersionForm({ agent, providers }: { agent: Agent; providers: Provider[] }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [toolsReady, setToolsReady] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending || !toolsReady) return;
    setError(""); setPending(true);
    try {
      await postApi(`/agents/${agent.id}/versions`, {
        ...configFromForm(new FormData(event.currentTarget)),
        planner: agent.latest_version.planner,
      });
      router.refresh();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not create version"); }
    finally { setPending(false); }
  }
  return <details className="border-t pt-3"><summary className="cursor-pointer text-sm text-blue-700">Create new immutable version</summary><form key={agent.latest_version.id} onSubmit={submit} className="mt-4 space-y-4" aria-busy={pending}><p className="text-xs">Copies version {agent.latest_version.version} into a new configuration, preserving history. Existing runs and versions are never changed. Saving does not execute a task; new runs use the latest version.</p><fieldset disabled={pending}><ConfigFields initial={agent.latest_version} providers={providers} onToolsReady={setToolsReady} /></fieldset>{error && <p role="alert" className="text-sm text-red-700">{error}</p>}<Button type="submit" disabled={pending || !toolsReady}>{pending ? "Saving…" : "Save new version"}</Button></form></details>;
}
