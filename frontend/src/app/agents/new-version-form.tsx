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
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(""); setPending(true);
    try {
      await postApi(`/agents/${agent.id}/versions`, {
        ...configFromForm(new FormData(event.currentTarget)),
        planner: agent.latest_version.planner, tools: agent.latest_version.tools,
      });
      router.refresh();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not create version"); }
    finally { setPending(false); }
  }
  return <details className="border-t pt-3"><summary className="cursor-pointer text-sm text-blue-700">Create new immutable version</summary><form key={agent.latest_version.id} onSubmit={submit} className="mt-4 space-y-4"><p className="text-xs">Copies version {agent.latest_version.version}. Existing runs and versions are never changed.</p><ConfigFields initial={agent.latest_version} providers={providers} />{error && <p role="alert" className="text-sm text-red-700">{error}</p>}<Button type="submit" disabled={pending}>{pending ? "Saving…" : "Save new version"}</Button></form></details>;
}
