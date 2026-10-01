import assert from "node:assert/strict";
import { test } from "node:test";
import { existsSync } from "node:fs";
import { readFileSync } from "node:fs";

test("immutable configuration serializes selected versioned tools, including an empty selection", async () => {
  assert.ok(existsSync(new URL("../src/lib/agent-config.ts", import.meta.url)), "form serialization must be shared without React dependencies");
  const { configFromForm } = await import("../src/lib/agent-config.ts");
  const data = new FormData();
  data.set("instructions", "  Work safely  ");
  data.set("max_steps", "12");
  data.append("tools", "calculator@1");
  data.append("tools", "filesystem_write@1");
  const config = configFromForm(data);
  assert.deepEqual(config.tools, ["calculator@1", "filesystem_write@1"]);
  assert.equal(config.instructions, "Work safely");
  assert.equal(config.max_steps, 12);
  assert.equal(config.max_tokens, null);
  data.delete("tools");
  assert.deepEqual(configFromForm(data).tools, []);
});

test("new versions submit form selection rather than overriding tools with the old version", () => {
  const source = readFileSync(new URL("../src/app/agents/new-version-form.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(source, /tools:\s*agent\.latest_version\.tools/);
});

test("agent forms fetch the catalog and render versioned native checkbox values", () => {
  const source = readFileSync(new URL("../src/app/agents/config-fields.tsx", import.meta.url), "utf8");
  assert.match(source, /getApi<Tool\[\]>\("\/tools"\)/);
  assert.match(source, /type="checkbox" name="tools" value=\{tool\.key\}/);
  assert.match(source, /initial\?\.tools/);
  assert.match(source, /not a sandbox/);
});
