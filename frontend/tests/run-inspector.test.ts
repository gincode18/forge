/* eslint-disable @typescript-eslint/no-explicit-any -- VM hook slots and JSX props are intentionally dynamic. */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { test } from "node:test";
import { runInNewContext } from "node:vm";
import ts from "typescript";
import * as api from "../src/lib/api.ts";
import * as trace from "../src/lib/run-trace.ts";

const require = createRequire(import.meta.url);
const compiled = ts.transpileModule(readFileSync(new URL("../src/app/runs/[id]/run-inspector.tsx", import.meta.url), "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
}).outputText;

type Element = { type: unknown; props: Record<string, any> };
const approval = { id: "approval-1", run_id: "run-1", step_id: "step-1", tool_name: "filesystem_write", tool_version: "1", arguments: { path: "answer.txt", content: "14" }, status: "pending", created_at: "2026-09-30", resolved_at: null };
const artifact = { id: "artifact-1", run_id: "run-1", path: "answer.txt", size_bytes: 2, media_type: "text/plain", created_at: "2026-09-30" };

// Exercise the real component's handlers/effects with deterministic hook slots.
// No DOM, backend, provider credentials, or additional test dependencies needed.
function inspector(status = "waiting_for_approval") {
  const slots: any[] = [];
  let index = 0;
  let effects: (() => void)[] = [];
  const reads: string[] = [];
  const writes: { path: string; body: object }[] = [];
  const run = { id: "run-1", agent_version_id: "version-1", input: "demo", status, created_at: "2026-09-30" };
  let approvals = [{ ...approval }];
  let artifacts = [{ ...artifact }];
  let post = async () => ({ ...approval, status: "approved" });
  const streams: FakeStream[] = [];
  class FakeStream {
    onopen?: () => void;
    onerror?: () => void;
    listeners = new Map<string, (event: { data: string }) => void>();
    constructor() { streams.push(this); }
    addEventListener(name: string, listener: (event: { data: string }) => void) { this.listeners.set(name, listener); }
    close() {}
    emit(type: string) { this.listeners.get(type)?.({ data: JSON.stringify({ id: "event-1", sequence: 1, type, payload: {} }) }); }
  }
  const hooks = {
    useState(initial: any) {
      const key = index++;
      if (!(key in slots)) slots[key] = typeof initial === "function" ? initial() : initial;
      return [slots[key], (value: any) => { slots[key] = typeof value === "function" ? value(slots[key]) : value; }];
    },
    useRef(initial: any) {
      const key = index++;
      if (!(key in slots)) slots[key] = { current: initial };
      return slots[key];
    },
    useCallback(callback: any) { index++; return callback; },
    useEffect(callback: () => void, deps: any[]) {
      const key = index++;
      const previous = slots[key];
      // Callback identity is ignored: useCallback above preserves behavior, not identity.
      const stableDeps = deps.filter((dep) => typeof dep !== "function");
      if (!previous || stableDeps.some((dep, i) => dep !== previous[i])) effects.push(callback);
      slots[key] = stableDeps;
    },
  };
  const jsx = (type: unknown, props: Element["props"]) => ({ type, props });
  const componentModule = { exports: {} as { RunInspector: (props: any) => Element } };
  runInNewContext(compiled, {
    module: componentModule, exports: componentModule.exports, EventSource: FakeStream, Error,
    require(name: string) {
      if (name === "react") return hooks;
      if (name === "react/jsx-runtime") return { jsx, jsxs: jsx };
      if (name === "@/lib/run-trace") return trace;
      if (name === "@/lib/api") return {
        ...api,
        async getApi(path: string) {
          reads.push(path);
          if (path.endsWith("/approvals")) return approvals;
          if (path.endsWith("/artifacts")) return artifacts;
          if (path.endsWith("/steps") || path.endsWith("/events")) return [];
          return { ...run };
        },
        async postApi(path: string, body: object) { writes.push({ path, body: JSON.parse(JSON.stringify(body)) }); return post(); },
      };
      if (name === "next/link") return { default: "a" };
      if (name.startsWith("@/components/")) return new Proxy({}, { get: (_, key) => String(key) });
      return require(name);
    },
  });
  function render() {
    index = 0;
    const tree = componentModule.exports.RunInspector({ initialRun: run, initialEvents: [], initialSteps: [] });
    const pending = effects; effects = []; pending.forEach((effect) => effect());
    return tree;
  }
  function nodes(tree: any): Element[] {
    if (Array.isArray(tree)) return tree.flatMap(nodes);
    if (!tree || typeof tree !== "object" || !tree.props) return [];
    return [tree, ...nodes(tree.props.children)];
  }
  const find = (label: string) => nodes(render()).find((node) => node.props.children === label);
  const settle = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
  return { render, nodes, find, settle, reads, writes, streams, run,
    setPost(fn: typeof post) { post = fn; },
    setApprovals(value: typeof approvals) { approvals = value; },
    setArtifacts(value: typeof artifacts) { artifacts = value; },
  };
}

test("historical inspector loads approvals/artifacts and manual refresh fetches the full trace", async () => {
  const view = inspector("completed");
  view.render(); await view.settle();
  assert.ok(view.reads.includes("/runs/run-1/approvals"));
  assert.ok(view.reads.includes("/runs/run-1/artifacts"));
  assert.equal(view.streams.length, 0);
  const refresh = view.find("Refresh trace"); assert.ok(refresh);
  await refresh.props.onClick();
  assert.ok(view.reads.includes("/runs/run-1/events"));
  const link = view.nodes(view.render()).find((node) => node.props.href?.includes("/artifacts/artifact-1"));
  assert.ok(link, "recorded artifact has a direct binary download link");
  assert.match(link.props.href, /\/api\/v1\/runs\/run-1\/artifacts\/artifact-1$/);
});

test("approval commands submit an explicit decision, block duplicate clicks, and refresh a conflict", async () => {
  const view = inspector();
  view.render(); view.streams[0].onopen?.(); await view.settle();
  const approve = view.find("Approve"); const reject = view.find("Reject");
  assert.ok(approve); assert.ok(reject);
  let fail!: (error: Error) => void;
  view.setPost(() => new Promise((_, reject) => { fail = reject; }));
  const pending = approve.props.onClick();
  await approve.props.onClick();
  await reject.props.onClick();
  assert.equal(view.writes.length, 1);
  assert.deepEqual(view.writes[0], { path: "/approvals/approval-1/resolve", body: { approved: true } });
  assert.equal(view.find("Reject")?.props.disabled, true);
  view.setApprovals([{ ...approval, status: "rejected" }]);
  const before = view.reads.length;
  fail(new Error("Forge API returned 409")); await pending;
  assert.ok(view.reads.slice(before).includes("/runs/run-1/approvals"));
  assert.equal(view.find("Approve"), undefined);
  assert.ok(view.nodes(view.render()).some((node) => node.props.role === "alert"));
});

test("reject submits false and relevant SSE events and reconnect refresh durable controls", async () => {
  const view = inspector();
  view.render(); const stream = view.streams[0]; stream.onopen?.(); await view.settle();
  for (const event of ["approval.requested", "approval.resolved", "approval.cancelled", "artifact.created", "run.paused", "run.resumed"]) {
    const before = view.reads.length; stream.emit(event); await view.settle();
    assert.ok(view.reads.slice(before).includes("/runs/run-1/approvals"), event);
    assert.ok(view.reads.slice(before).includes("/runs/run-1/artifacts"), event);
  }
  const before = view.reads.length; stream.onopen?.(); await view.settle();
  assert.ok(view.reads.slice(before).includes("/runs/run-1/approvals"));
  const reject = view.find("Reject"); assert.ok(reject); await reject.props.onClick();
  assert.deepEqual(view.writes[0], { path: "/approvals/approval-1/resolve", body: { approved: false } });
});

test("artifact downloads encode identifiers without using filesystem paths", () => {
  const download = (api as Record<string, any>).artifactDownloadUrl;
  assert.equal(typeof download, "function");
  assert.equal(download("run /?", "artifact #"), `${api.API_BASE}/api/v1/runs/run%20%2F%3F/artifacts/artifact%20%23`);
});
