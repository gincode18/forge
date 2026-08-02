import {
  Activity,
  ArrowUpRight,
  Bot,
  Boxes,
  CircleCheckBig,
  Code2,
  Terminal,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

const foundations = [
  {
    name: "Runtime",
    description: "Execute agents through one explicit control loop.",
    icon: Activity,
  },
  {
    name: "Tool system",
    description: "Register capabilities and enforce policies per run.",
    icon: Terminal,
  },
  {
    name: "Observability",
    description: "Capture events, decisions, cost, and execution traces.",
    icon: Boxes,
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_50%_-20%,#dbeafe_0,transparent_34%),linear-gradient(180deg,#f8fafc_0%,#ffffff_45%)] px-5 py-8 text-slate-950 sm:px-10 lg:px-16">
      <div className="mx-auto flex max-w-6xl flex-col gap-14">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-slate-950 text-white shadow-lg shadow-slate-950/15">
              <Code2 className="size-5" aria-hidden="true" />
            </div>
            <span className="text-lg font-semibold tracking-tight">Forge</span>
          </div>
          <Badge variant="outline" className="gap-1.5 border-emerald-200 bg-emerald-50 px-2.5 text-emerald-700">
            <span className="size-1.5 rounded-full bg-emerald-500" />
            Local mode
          </Badge>
        </header>

        <section className="grid items-end gap-10 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="max-w-2xl">
            <Badge variant="secondary" className="mb-5 bg-blue-50 text-blue-700">
              Agent runtime workspace
            </Badge>
            <h1 className="text-4xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-5xl">
              Build agents you can inspect, control, and trust.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
              Forge is the local-first foundation for running AI agents. The
              dashboard will make every tool call, decision, and run visible.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button size="lg" className="bg-slate-950 shadow-lg shadow-slate-950/15 hover:bg-slate-800">
                Create your first agent
                <ArrowUpRight className="size-4" aria-hidden="true" />
              </Button>
              <Button
                variant="outline"
                size="lg"
                nativeButton={false}
                render={
                  <a
                    href="http://localhost:8000/docs"
                    target="_blank"
                    rel="noreferrer"
                  />
                }
              >
                Open API docs
              </Button>
            </div>
          </div>

          <Card className="border-0 bg-slate-950 py-0 text-slate-50 shadow-2xl shadow-slate-900/20 ring-1 ring-slate-800">
            <CardHeader className="px-6 pt-6">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base text-white">Runtime status</CardTitle>
                <CircleCheckBig className="size-5 text-emerald-400" aria-hidden="true" />
              </div>
              <CardDescription className="text-slate-400">
                Local development environment
              </CardDescription>
            </CardHeader>
            <CardContent className="px-6 pb-6 pt-2">
              <Separator className="mb-5 bg-slate-800" />
              <dl className="space-y-4 text-sm">
                <div className="flex items-center justify-between">
                  <dt className="text-slate-400">API service</dt>
                  <dd className="font-medium text-emerald-300">Ready</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-slate-400">Storage</dt>
                  <dd className="font-medium text-slate-100">SQLite · next step</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-slate-400">Agent runs</dt>
                  <dd className="font-medium text-slate-100">Not created</dd>
                </div>
              </dl>
            </CardContent>
          </Card>
        </section>

        <section>
          <div className="mb-5 flex items-center gap-3">
            <Bot className="size-5 text-blue-600" aria-hidden="true" />
            <h2 className="font-semibold tracking-tight">Forge foundations</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {foundations.map(({ name, description, icon: Icon }) => (
              <Card key={name} className="bg-white/80 shadow-sm">
                <CardHeader>
                  <div className="mb-2 grid size-9 place-items-center rounded-lg bg-blue-50 text-blue-700">
                    <Icon className="size-4" aria-hidden="true" />
                  </div>
                  <CardTitle>{name}</CardTitle>
                  <CardDescription className="leading-6">{description}</CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
