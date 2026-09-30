# Gemini model selection for Forge

Checked September 30, 2026 against Google's model and pricing documentation.
This is a recommendation, not a Forge quality benchmark; no live model calls
were made during this comparison.

| Model ID | Standard text input / 1M tokens | Output / 1M tokens (includes thinking) | Suggested role |
| --- | ---: | ---: | --- |
| `gemini-3.1-flash-lite` | $0.25 | $1.50 | Lowest-cost extraction/classification baseline |
| `gemini-3.5-flash-lite` | $0.30 | $2.50 | Summaries, translation, routine high-volume tasks |
| `gemini-3.8-flash` | $0.75 | $3.75 | Candidate default for agent planning and coding tasks |

The 3.8 prices above last through December 31, 2026; starting January 1,
2027, Google lists $1.50 input and $7.50 output. Do not freeze promotional
prices into permanent cost accounting. At 2,000 input and 500 billed output
tokens per call, 1,000 calls cost $1.25, $1.85, or $3.375 respectively, excluding
other charges. Thinking tokens can increase billed output beyond visible text.

Recommendation: try `gemini-3.8-flash` for the main agent and retain Lite for
simple tasks. Google positions 3.8 for software engineering and autonomous
agents; verify this on our own small task set before claiming a quality gain.
The adapter accepts each immutable version's model ID; no new provider is
needed to compare models. Do not rewrite old agent versions.

Use synthetic inputs on the free tier: Google lists free-tier content as used
to improve products and paid-tier content as not used for that purpose.
Grounding, cache storage, and other features have separate charges.

## Sources

- Google standard pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini 3.8 capabilities and stable ID: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash

## Scope

A model recommendation does not complete Phase 3. The current PR remains the
first no-tool completion slice; streaming, planner-loop semantics, limits,
retry accounting, provider selection UI, and live smoke verification remain.
