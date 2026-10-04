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
function inspector(status = "waiting_for_approval", initialEvents: api.RunEvent[] = [], initialSteps: api.RunStep[] = []) {
  const slots: any[] = [];
  let index = 0;
  let effects: (() => void)[] = [];
  const reads: string[] = [];
  const writes: { path: string; body: object }[] = [];
  const run = { id: "run-1", agent_version_id: "version-1", input: "demo", status, created_at: "2026-09-30" };
  let approvals = [{ ...approval }];
  let artifacts: api.Artifact[] = [{ ...artifact }];
  let post = async () => ({ ...approval, status: "approved" });
  const streams: FakeStream[] = [];
  class FakeStream {
    onopen?: () => void;
    onerror?: () => void;
    listeners = new Map<string, (event: { data: string }) => void>();
    constructor() { streams.push(this); }
    addEventListener(name: string, listener: (event: { data: string }) => void) { this.listeners.set(name, listener); }
    close() {}
    emit(type: string, value = { id: "event-1", sequence: 1, type, payload: {} }) { this.listeners.get(type)?.({ data: JSON.stringify(value) }); }
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
          if (path.endsWith("/steps")) return initialSteps;
          if (path.endsWith("/events")) return initialEvents;
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
    const tree = componentModule.exports.RunInspector({ initialRun: run, initialEvents, initialSteps });
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

function text(node: any): string {
  if (Array.isArray(node)) return node.map(text).join(" ");
  if (node && typeof node === "object") return text(node.props?.children);
  return node == null || typeof node === "boolean" ? "" : String(node);
}
function timeline(view: ReturnType<typeof inspector>) {
  return view.nodes(view.render()).find(node => node.props["aria-label"] === "Event timeline")!;
}

test("workspace guidance explains run-scoped files without pretending to know the host data directory", () => {
  const view = inspector("queued");
  const workspace = view.nodes(view.render()).find(node => node.props["aria-label"] === "Run workspace");
  assert.ok(workspace);
  assert.match(text(workspace), /workspaces\/run-1/);
  assert.match(text(workspace), /FORGE_DATA_DIR/);
  assert.match(text(workspace), /separate workspace/i);
  assert.match(text(workspace), /not a sandbox/i);
});

test("timeline filters are accessible, chronological, preserve safe raw data and do not interrupt SSE", async () => {
  const events = [
    {id: "3", sequence: 3, type: "tool.denied", payload: {step_id: "tool-1", tool_name: "filesystem_write", reason: "not_allowed", api_key: "synthetic"}, created_at: "2026-10-01T10:01:02Z"},
    {id: "1", sequence: 1, type: "model.completed", payload: {provider: "fake", model: "deterministic"}},
    {id: "2", sequence: 2, type: "planner.decided", payload: {action: "continue"}},
  ];
  const view = inspector("running", events);
  view.render(); await view.settle();
  for (const label of trace.eventFilters) {
    assert.ok(view.find(label), `${label} filter exists`);
    assert.equal(view.find(label)?.props["aria-pressed"], label === "All");
  }
  const all = text(timeline(view));
  assert.ok(all.indexOf("Model response completed") < all.indexOf("Planner chose an action"));
  assert.match(all, /filesystem_write.*not_allowed/);
  assert.match(all, /2026-10-01T10:01:02Z/);
  assert.match(all, /Timestamp unknown/);
  assert.match(all, /\[redacted\]/);
  assert.ok(!all.includes("synthetic"));
  await view.find("Tools")!.props.onClick();
  assert.equal(view.find("Tools")!.props["aria-pressed"], true);
  assert.ok(!text(timeline(view)).includes("Model response completed"));
  assert.match(text(timeline(view)), /Tool denied/);
  await view.find("Approvals")!.props.onClick();
  assert.match(text(timeline(view)), /No approvals events/);
  await view.find("All")!.props.onClick();
  assert.match(text(timeline(view)), /Model response completed/);
  assert.equal(view.streams.length, 1, "filters do not reopen the live stream");
});

test("terminal diagnosis links only explicitly identified steps and gives a next action", async () => {
  const step: api.RunStep = {id: "actual /step", sequence: 1, attempt: 1, kind: "model", status: "failed", input: {}, output: null, error: {message: "Provider unavailable"}};
  const view = inspector("failed", [{id: "failure", sequence: 2, type: "run.failed", payload: {reason: "error", step_id: step.id}}], [step]);
  view.render(); await view.settle();
  const outcome = view.nodes(view.render()).find(node => node.props["aria-label"] === "Run diagnosis");
  assert.ok(outcome);
  assert.match(text(outcome), /Provider unavailable/);
  assert.match(text(outcome), /Next action/);
  const link = view.nodes(outcome).find(node => node.props.href?.startsWith("#step-"));
  assert.equal(link?.props.href, "#step-actual%20%2Fstep");
  assert.ok(view.nodes(view.render()).some(node => node.props.id === "step-actual%20%2Fstep"));
  assert.match(text(outcome), /Failed boundary:.*#1.*model/);
  const failedCard = view.nodes(view.render()).find(node => node.props.id === "step-actual%20%2Fstep")!;
  assert.match(failedCard.props.className, /border-amber/);
  assert.equal(view.nodes(failedCard).filter(node => node.type === "details").every(node => node.props.open === true), true, "causal error details open by default");
  const budget = inspector("failed", [{id: "budget", sequence: 3, type: "run.failed", payload: {reason: "max_steps"}}], [step]);
  const diagnosis = budget.nodes(budget.render()).find(node => node.props["aria-label"] === "Run diagnosis")!;
  assert.match(text(diagnosis), /step limit/);
  assert.match(text(diagnosis), /No exact step linked/);
  assert.equal(budget.nodes(diagnosis).filter(node => node.props.href?.startsWith("#step-")).length, 0);
});

test("diagnosis follows envelope causation with navigable event and step boundaries and debug IDs", () => {
  const step: api.RunStep = {id: "s", sequence: 1, attempt: 1, kind: "model", status: "failed", input: {}, output: null, error: {message: "offline"}};
  const events = [
    {...{id: "request", sequence: 1, type: "model.requested", payload: {}}, step_id: "s", causation_id: null, trace_id: "trace-one", span_id: "span-one", correlation_id: "corr-one"},
    {...{id: "failure", sequence: 2, type: "model.failed", payload: {}}, step_id: "s", causation_id: "request"},
    {...{id: "terminal", sequence: 3, type: "run.failed", payload: {reason: "error"}}, step_id: "s", causation_id: "failure"},
  ];
  const view = inspector("failed", events, [step]);
  const diagnosis = view.nodes(view.render()).find(node => node.props["aria-label"] === "Run diagnosis")!;
  assert.match(text(diagnosis), /Causal chain/);
  assert.deepEqual(view.nodes(diagnosis).filter(node => node.props.href?.startsWith("#event-")).map(node => node.props.href), ["#event-request", "#event-failure", "#event-terminal"]);
  assert.ok(view.nodes(view.render()).some(node => node.props.id === "event-request"));
  assert.match(text(timeline(view)), /trace-one[\s\S]*span-one/);
  assert.match(text(diagnosis), /Failed boundary: Step #1/);
  const request = view.nodes(timeline(view)).find(node => node.props.id === "event-request")!;
  assert.ok(view.nodes(request).some(node => node.props.href === "#step-s"), "envelope step ID links the event boundary");
});

test("diagnosis shows incomplete causal history without blaming predecessor steps", () => {
  const view = inspector("failed", [{id: "terminal", sequence: 1, type: "run.failed", payload: {reason: "max_steps"}, causation_id: "missing"}]);
  const diagnosis = view.nodes(view.render()).find(node => node.props["aria-label"] === "Run diagnosis")!;
  assert.match(text(diagnosis), /Missing causal event: missing/);
  assert.match(text(diagnosis), /No exact step linked/);
});

test("timeline renders latest 100, expands earlier in bounded pages and resets on filter changes", async () => {
  const events = Array.from({length: 1200}, (_, index) => ({id: String(index + 1), sequence: index + 1, type: index % 2 ? "tool.completed" : "model.completed", payload: {}}));
  const view = inspector("completed", events);
  const rows = () => view.nodes(timeline(view)).filter(node => node.type === "li");
  assert.equal(rows().length, 100);
  assert.match(text(timeline(view)), /100 shown of 1200 All events/);
  assert.equal(rows()[0].props.id, "event-1101");
  await view.find("Show earlier 100")!.props.onClick();
  assert.equal(rows().length, 200);
  await view.find("Refresh trace")!.props.onClick();
  assert.equal(rows().length, 200, "refresh preserves the visible window");
  for (let i = 0; i < 3; i++) await view.find("Show earlier 100")!.props.onClick();
  assert.equal(rows().length, 500);
  await view.find("Earlier page")!.props.onClick();
  assert.equal(rows().length, 500);
  assert.equal(rows()[0].props.id, "event-201");
  await view.find("Tools")!.props.onClick();
  assert.equal(rows().length, 100);
  assert.match(text(timeline(view)), /100 shown of 600 Tools events/);
  await view.find("All")!.props.onClick();
  assert.equal(rows().length, 100);
  assert.equal(rows()[0].props.id, "event-1101");
});

test("live timeline preserves last expanded event across rolling windows, filters and refresh without delta fetches", async () => {
  const events = Array.from({length: 101}, (_, index) => ({id: String(index + 1), sequence: index + 1, type: "model.delta", payload: {step_id: "s", text: "x"}}));
  const view = inspector("running", events);
  view.render(); await view.settle();
  const row = view.nodes(timeline(view)).find(node => node.props.id === "event-2")!;
  view.nodes(row).find(node => node.type === "details")!.props.onToggle({currentTarget: {open: true}});
  const before = view.reads.length;
  view.streams[0].emit("model.delta", {id: "102", sequence: 102, type: "model.delta", payload: {step_id: "s", text: "y"}});
  await view.settle();
  assert.equal(view.reads.length, before, "model deltas must not refresh durable API state");
  const rows = view.nodes(timeline(view)).filter(node => node.type === "li");
  assert.equal(rows.length, 101, "only one expanded row is retained beyond the page bound");
  assert.equal(rows[0].props.id, "event-2");
  assert.equal(view.nodes(rows[0]).find(node => node.type === "details")!.props.open, true);
  await view.find("Tools")!.props.onClick();
  assert.equal(view.nodes(timeline(view)).filter(node => node.type === "li").length, 0);
  await view.find("All")!.props.onClick();
  await view.find("Refresh trace")!.props.onClick();
  const restored = view.nodes(timeline(view)).find(node => node.props.id === "event-2")!;
  assert.equal(view.nodes(restored).find(node => node.type === "details")!.props.open, true);
});

test("causal links reveal off-window events without unbounding the timeline", () => {
  const events: api.RunEvent[] = Array.from({length: 1200}, (_, index) => ({id: String(index + 1), sequence: index + 1, type: "model.completed", payload: {}, causation_id: index ? String(index) : null, schema_version: 2}));
  events[1199].type = "run.failed";
  const view = inspector("failed", events);
  const chain = view.nodes(view.render()).find(node => node.props["aria-label"] === "Causal chain")!;
  assert.equal(view.nodes(chain).filter(node => node.type === "li").length, 100);
  assert.match(text(chain), /100 shown of 1200 causal events/);
  const link = view.nodes(chain).find(node => node.props.href === "#event-1101")!;
  view.find("Tools")!.props.onClick();
  link.props.onClick({preventDefault() {}});
  const rows = view.nodes(timeline(view)).filter(node => node.type === "li");
  assert.equal(rows.length, 100);
  assert.ok(rows.some(node => node.props.id === "event-1101"));
  assert.equal(view.find("All")!.props["aria-pressed"], true);
});

test("summary displays failed boundaries and timestamp model timing", () => {
  const step: api.RunStep = {id: "m", sequence: 1, attempt: 1, kind: "model", status: "failed", input: {}, output: null, error: null, started_at: "2026-10-01T10:00:00Z", finished_at: "2026-10-01T10:00:02Z"};
  const view = inspector("failed", [], [step]);
  const summary = view.nodes(view.render()).find(node => node.props["aria-label"] === "Run summary")!;
  assert.match(text(summary), /Step failures 1/);
  assert.match(text(summary), /Model failures 1/);
  assert.match(text(summary), /Planner failures 0/);
  assert.match(text(view.nodes(view.render()).find(node => node.props["aria-label"] === "Model metrics")), /Model latency 2,000 ms/);
});

test("artifact expiration SSE refreshes durable status and removes download links", async () => {
  const view = inspector("running");
  view.render(); await view.settle();
  view.setArtifacts([{...artifact, expired: true}]);
  const before = view.reads.length;
  view.streams[0].emit("artifact.expired", {id: "expired", sequence: 1, type: "artifact.expired", payload: {artifact_id: artifact.id}});
  await view.settle();
  assert.ok(view.reads.slice(before).includes("/runs/run-1/artifacts"));
  const section = view.nodes(view.render()).find(node => node.props["aria-label"] === "Artifacts")!;
  assert.match(text(section), /Expired by retention/);
  assert.equal(view.nodes(section).some(node => node.props.download), false);
});

test("retention markers explain expired historical data without reconstructing stale model output", () => {
  const expired = {retained: false, reason: "retention_expired"};
  const step: api.RunStep = {id: "m", sequence: 1, attempt: 1, kind: "model", status: "completed", input: expired, output: {text: expired, usage: {total_tokens: 7}, cost_usd: 0}, error: null};
  const view = inspector("completed", [
    {id: "old", sequence: 1, type: "model.delta", payload: {step_id: "m", text: "stale replay text"}},
    {id: "expired", sequence: 2, type: "model.delta", payload: expired, step_id: "m"},
    {id: "terminal", sequence: 3, type: "run.completed", payload: {result: expired}},
  ], [step]);
  const rendered = text(view.render());
  assert.match(rendered, /Data expired by retention/);
  assert.ok(!rendered.includes("stale replay text"));
  assert.ok(!rendered.includes("No result recorded"));
  assert.ok(!rendered.includes("No model output recorded"));
  assert.match(rendered, /historical trace is incomplete/i);
});

test("summary displays duration and disjoint tool outcomes without changing unknown model metrics", async () => {
  const steps: api.RunStep[] = [{id: "denied", sequence: 1, attempt: 1, kind: "tool", status: "failed", input: {}, output: null, error: null}];
  const view = inspector("failed", [
    {id: "start", sequence: 1, type: "run.started", payload: {}, created_at: "2026-10-01T10:00:00Z"},
    {id: "deny", sequence: 2, type: "tool.denied", payload: {step_id: "denied"}},
    {id: "fail", sequence: 3, type: "run.failed", payload: {reason: "max_steps"}, created_at: "2026-10-01T10:00:02.500Z"},
  ], steps);
  view.render(); await view.settle();
  const summary = view.nodes(view.render()).find(node => node.props["aria-label"] === "Run summary");
  assert.ok(summary);
  assert.match(text(summary), /Duration 2.5 s/);
  assert.match(text(summary), /Tools completed 0/);
  assert.match(text(summary), /Tools denied 1/);
  assert.match(text(summary), /Tools failed 0/);
  const metrics = view.nodes(view.render()).find(node => node.props["aria-label"] === "Model metrics");
  assert.match(text(metrics), /Estimated cost Unknown/);
  const live = inspector("running");
  assert.match(text(live.nodes(live.render()).find(node => node.props["aria-label"] === "Run summary")), /Duration Unknown/);
});

test("filtered live timeline still receives named SSE events and durable approval/artifact refreshes", async () => {
  const view = inspector();
  view.render(); await view.settle();
  await view.find("Errors")!.props.onClick();
  const stream = view.streams[0];
  stream.emit("tool.denied", {id: "denied", sequence: 2, type: "tool.denied", payload: {tool_name: "filesystem_write", step_id: "tool-1", reason: "approval_rejected"}});
  await view.settle();
  assert.match(text(timeline(view)), /Tool denied.*filesystem_write.*approval_rejected/);
  assert.ok(view.find("Approve"), "filtering does not hide approval controls");
  const before = view.reads.length;
  stream.emit("artifact.created", {id: "artifact", sequence: 3, type: "artifact.created", payload: {}});
  await view.settle();
  assert.ok(view.reads.slice(before).includes("/runs/run-1/artifacts"));
  assert.ok(!text(timeline(view)).includes("Artifact recorded"));
  await view.find("All")!.props.onClick();
  assert.match(text(timeline(view)), /Artifact recorded/);
  assert.ok(view.nodes(view.render()).some(node => node.props.href?.includes("/artifacts/artifact-1")));
});
