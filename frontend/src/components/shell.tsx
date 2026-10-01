import Link from "next/link";
import { Code2 } from "lucide-react";

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#fff_50%)] px-5 py-8 text-slate-950 sm:px-10 lg:px-16">
      <div className="mx-auto max-w-6xl">
        <header className="mb-12 flex flex-wrap items-center justify-between gap-5 border-b border-slate-200 pb-6">
          <Link href="/" className="flex items-center gap-3 font-semibold tracking-tight">
            <span className="grid size-10 place-items-center rounded-xl bg-slate-950 text-white"><Code2 className="size-5" aria-hidden="true" /></span>
            Forge
          </Link>
          <nav aria-label="Main navigation" className="flex gap-5 text-sm font-medium text-slate-600">
            <Link className="hover:text-slate-950" href="/">Dashboard</Link>
            <Link className="hover:text-slate-950" href="/agents">Agents</Link>
            <Link className="hover:text-slate-950" href="/runs">Runs</Link>
            <Link className="hover:text-slate-950" href="/tools">Tools</Link>
          </nav>
        </header>
        {children}
      </div>
    </main>
  );
}
