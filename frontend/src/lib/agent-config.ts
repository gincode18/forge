export const limits = [
  ["timeout_seconds", "Timeout (seconds)", 30, 0.001, undefined, "any"],
  ["max_steps", "Maximum steps", 12, 1, 100, "1"],
  ["max_output_tokens", "Output tokens / request", 2048, 1, undefined, "1"],
  ["max_retries", "Retries / request", 2, 0, 5, "1"],
  ["max_tokens", "Run token budget (optional)", null, 1, undefined, "1"],
  ["max_cost_usd", "Run cost budget, USD (optional)", null, 0.000001, undefined, "any"],
  ["input_cost_per_million", "Input USD / million tokens", null, 0, undefined, "any"],
  ["output_cost_per_million", "Output USD / million tokens", null, 0, undefined, "any"],
] as const;

export function configFromForm(data: FormData) {
  const values: Record<string, string | string[] | number | null> = {
    instructions: String(data.get("instructions") ?? "").trim(),
    provider: String(data.get("provider") ?? "fake").trim(),
    model: String(data.get("model") ?? "deterministic").trim(),
    tools: data.getAll("tools").map(String),
  };
  for (const [key] of limits) {
    const value = String(data.get(key) ?? "").trim();
    values[key] = value ? Number(value) : null;
  }
  if (values.max_cost_usd !== null && (values.input_cost_per_million === null || values.output_cost_per_million === null)) {
    throw new Error("A cost budget requires both explicit pricing rates. Forge does not assume vendor pricing.");
  }
  return values;
}
