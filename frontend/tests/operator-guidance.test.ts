/* eslint-disable @typescript-eslint/no-explicit-any -- Lightweight JSX/React hook harness without browser dependencies. */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { test } from "node:test";
import { runInNewContext } from "node:vm";
import ts from "typescript";

const require = createRequire(import.meta.url);
type Element = { type: unknown; props: Record<string, any> };
const agent = { id: "agent-1", name: "Demo", latest_version: { id: "version-1", version: 1, provider: "fake", model: "deterministic", tools: [], instructions: "Be helpful" } };
function component(file: string, name: string, props: any = {}) {
  const slots: any[] = [];
  let index = 0;
  const writes: { path: string; body: any }[] = [];
  const pushes: string[] = [];
  const jsx = (type: unknown, props: Element["props"]) => ({ type, props });
  const mod = { exports: {} as Record<string, any> };
  const compiled = ts.transpileModule(readFileSync(new URL(`../src/app/${file}.tsx`, import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  runInNewContext(compiled, { module: mod, exports: mod.exports, Error,
    FormData: class { form: any; constructor(form: any) { this.form = form; } get(key: string) { return this.form[key]; } },
    require(path: string) {
      if (path === "react/jsx-runtime") return { jsx, jsxs: jsx };
      if (path === "react") return {
        useId: () => "fields",
        useEffect: () => {},
        useState(initial: any) { const key = index++; if (!(key in slots)) slots[key] = initial; return [slots[key], (next: any) => { slots[key] = typeof next === "function" ? next(slots[key]) : next; }]; },
      };
      if (path === "next/navigation") return { useRouter: () => ({ push: (path: string) => pushes.push(path), refresh() {} }) };
      if (path === "next/link") return { default: "a" };
      if (path === "@/lib/api") return {
        getApi: async (path: string) => path === "/agents" ? [agent] : [],
        postApi: async (path: string, body: any) => { writes.push({ path, body }); return { id: "run-1" }; },
      };
      if (path === "@/lib/agent-config") return { limits: [], configFromForm: () => ({}) };
      if (path.startsWith("@/components/") || path.startsWith("./")) return new Proxy({}, { get: (_, key) => String(key) });
      return require(path);
    },
  });
  return { render() { index = 0; return mod.exports[name](props); }, writes, pushes };
}
function nodes(tree: any): Element[] {
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  return tree?.props ? [tree, ...nodes(tree.props.children)] : [];
}
function text(tree: any): string {
  if (Array.isArray(tree)) return tree.map(text).join(" ");
  if (tree?.props) return text(tree.props.children);
  return typeof tree === "string" || typeof tree === "number" ? String(tree) : "";
}
function describedHelp(tree: any, name: string) {
  const field = nodes(tree).find((node) => node.props.name === name);
  assert.ok(field, `field ${name}`);
  const ids = String(field.props["aria-describedby"] ?? "").split(" ");
  const help = nodes(tree).filter((node) => ids.includes(node.props.id));
  assert.ok(help.length, `${name} has associated help`);
  return text(help);
}

test("launch creates and starts a run with provider-specific help, while queue only creates", async () => {
  const launch = component("agents/launch-run-form", "LaunchRunForm", { agentId: agent.id, agentName: agent.name, provider: "fake" });
  const tree = launch.render();
  assert.match(describedHelp(tree, "input"), /creates.*starts/i);
  assert.match(text(tree), /deterministic test simulator/i);
  assert.match(text(tree), /does not reason/i);
  const example = nodes(tree).find((node) => node.type === "code");
  assert.ok(example, "scripted fake example");
  assert.deepEqual(JSON.parse(text(example)), { forge_script: [{ name: "calculator", arguments: { expression: "2 + 2" } }] });
  await tree.props.onSubmit({ preventDefault() {}, currentTarget: { input: "demo" } });
  assert.deepEqual(launch.writes.map((write) => write.path), ["/runs", "/runs/run-1/start"]);
  const gemini = component("agents/launch-run-form", "LaunchRunForm", { agentId: agent.id, agentName: agent.name, provider: "gemini" }).render();
  assert.doesNotMatch(text(gemini), /forge_script/);
  assert.match(describedHelp(gemini, "input"), /task/i);
  const page = await component("agents/page", "default").render();
  assert.equal(nodes(page).find((node) => node.type === "LaunchRunForm")?.props.provider, "fake");
  const queue = component("runs/queue-run-form", "QueueRunForm", { agents: [agent] });
  const queuedTree = queue.render();
  assert.match(describedHelp(queuedTree, "input"), /does not start/i);
  await queuedTree.props.onSubmit({ preventDefault() {}, currentTarget: { agent_id: agent.id, input: "demo", reset() {} } });
  assert.deepEqual(queue.writes.map((write) => write.path), ["/runs"]);
  assert.deepEqual(queue.pushes, ["/runs/run-1"]);
  const runs = await component("runs/page", "default").render();
  assert.doesNotMatch(text(runs), /fake-agent traces/);
  assert.match(text(runs), /execution traces/i);
});

test("tools catalog is read-only and explains enablement separately from invocation", async () => {
  const page = await component("tools/page", "default").render();
  assert.match(text(page), /read-only catalog/i);
  assert.match(text(page), /permits.*requests.*not.*guarantee.*invocation/i);
  assert.match(text(page), /Sensitive writes and subprocess calls require approval/);
  assert.match(text(page), /operator’s exact allowlist/);
  assert.match(text(page), /Local controls are not a sandbox or security boundary/);
  assert.ok(nodes(page).some((node) => node.props.href === "/agents"));
  assert.equal(nodes(page).some((node) => ["form", "input", "button"].includes(String(node.type))), false);
});

test("configuration explains instructions, simulator limits, and tool permission boundaries", () => {
  const tree = component("agents/config-fields", "ConfigFields", { providers: [], onToolsReady() {} }).render();
  assert.match(describedHelp(tree, "instructions"), /behavior.*not.*task/i);
  assert.match(describedHelp(tree, "provider"), /deterministic test simulator/i);
  assert.match(text(tree), /not.*natural-language.*model/i);
  assert.match(text(tree), /GEMINI_API_KEY.*backend/i);
  assert.match(text(tree), /permits.*requests.*not.*guarantee.*invocation/i);
  assert.match(text(tree), /Sensitive writes and subprocess.*approval/i);
  assert.match(text(tree), /subprocess.*operator.*allowlist/i);
  assert.match(text(tree), /Local controls are not a sandbox or security boundary/);
});

test("agent creation saves configuration without execution and version changes preserve history", async () => {
  const create = component("agents/create-agent-form", "CreateAgentForm", { providers: [] }).render();
  assert.match(text(create), /does not execute/i);
  const version = component("agents/new-version-form", "NewVersionForm", { agent, providers: [] }).render();
  assert.match(text(version), /history/i);
  assert.match(text(version), /Existing runs and versions are never changed/);
  const page = await component("agents/page", "default").render();
  assert.match(text(page), /Configure.*behavior.*run.*task/i);
});
