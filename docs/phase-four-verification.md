# Phase 4 verification

Phase 4's controlled local tool slice is implemented and verified offline. No
paid provider calls were made for this acceptance pass. Docker remains deferred.

## Automated gates

Parent independently reran:

- `backend/: uv run pytest -q` — **269 passed**, one existing Starlette/httpx
  deprecation warning.
- `backend/: uv run ruff check . ../scripts` — all checks passed.
- `frontend/: node --experimental-strip-types --test tests/*.test.ts` —
  **16 passed**, with existing module-type warnings.
- `frontend/: pnpm lint && pnpm build` — passed, including `/tools` route.
- `git diff --check` — passed.

The suite includes migration upgrade/downgrade, refusal of unsafe downgrade
with active approval/checkpoint state, disabled/unknown tool denial, pending
approval recovery, concurrent resolution, interrupted uncertain effects,
cancellation, limits, workspace path/symlink/hardlink checks and race regressions,
artifact tampering, subprocess process-group cleanup, immutable configurations,
accounting, and real Google SDK mock-HTTP tool-call/response serialization.

## Browser and CLI acceptance

Started the actual API and dashboard through `./forge start --offline` using
separate scratch data and custom ports (18104 / 13104). The built-in browser tool
was blocked by its real-profile/default-browser configuration. Used an isolated
Playwright environment and headless Chromium instead; did not change the user's
Hermes browser settings.

Browser exercised:

1. Create a fake agent from the form with `calculator@1` and
   `filesystem_write@1`; verify persisted immutable configuration.
2. Launch the documented deterministic two-tool script.
3. Observe `waiting_for_approval`, exact arguments, and enabled approval controls.
4. Reload while paused and approve from the recovered UI.
5. Observe final `Fake tool script completed`, no pending approval buttons,
   and downloadable `answer.txt` with exact bytes `14`.
6. Reload the historical trace and follow Tools navigation; verify explicit
   not-a-sandbox warning.
7. Assert no browser page errors.

Acceptance resource IDs (isolated scratch database, not normal operator data):

- Agent: `f16db2a1-91f3-474f-827b-86138fa99d9b`
- Run: `4241dbd8-7bbb-481b-a5a6-034c7124c5c4`
- Committed events: **30**, including approval resolution and artifact creation.

Then `./forge restart` retained the custom networking/offline configuration.
Read-back verified the same completed run, all 30 events, and artifact bytes `14`.
`./forge stop` shut down the smoke services cleanly. Earlier CLI coverage also
verified foreground Ctrl-C, duplicates, failed readiness, unrelated PID safety,
setup, and launches from outside the repository.

Ephemeral evidence and browser script are under
`/Users/gincode/.hermes/cache/scratch/forge-phase-four-final/` and may be pruned;
this document retains the acceptance findings.

## Scope and limitations

This is controlled **local execution**, not a sandbox. Approval authorizes a
specific call but cannot contain a malicious approved program. Some concurrent
filesystem/process races remain; writes are mutable, not crash-atomic artifact
snapshots. Uncertain interrupted side effects are not automatically replayed;
there is no exactly-once external-effect guarantee. Pending approval has no TTL;
waiting/downtime does not consume the saved execution-time budget. See ADR 0006.

Live Gemini no-tool acceptance remains the Phase 3 evidence. Phase 4 verifies
Gemini tool wire contracts offline, not account/model access through a paid live
tool run. The default suite remains no-key and offline.
