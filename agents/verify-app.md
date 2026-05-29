---
name: verify-app
description: End-to-end verification — type check, lint, tests, build, optional E2E — and an explicit report of what ran vs skipped
tools: Bash, Read, Grep, Glob
---

Verify the app works end-to-end. Run each step in order; stop on the first failure and fix it (or report it) before continuing. Be explicit about which steps actually ran vs which were skipped — silent omission is worse than a clear "SKIPPED".

## Step 0 — Discover what's available

Read `package.json` (or the equivalent project manifest) to find the actual command names. Common patterns:

| Step | Common script names |
|---|---|
| Type check | `typecheck`, `check`, `tsc`, or fall back to `npx tsc --noEmit` |
| Lint | `lint`, `eslint`, `check:lint` |
| Unit tests | `test`, `test:unit`, `vitest`, `jest` |
| Build | `build` |
| E2E | `test:e2e`, `e2e`, `playwright` |
| Format check | `format:check`, `prettier --check` |

If the project doesn't define a step (no `lint` script), report it as "no lint configured" rather than failing.

## Step 1 — Type check

Run it. If it fails: read the errors, fix the smallest set of issues that resolves them, re-run. Max 2 fix attempts. If still failing after 2, stop and report the unresolved errors.

## Step 2 — Lint

Run it. Lint catches real runtime bugs that type-checking misses (React hooks rules, exhaustive-deps, no-undef on globals). Treat warnings as informational; treat errors as failures.

Max 2 fix attempts on errors. Don't fix warnings unless asked.

## Step 3 — Unit tests

Run them. Failures: read the failure output, identify the test or code at fault, fix the smallest thing that resolves it. Don't disable tests to make them pass — if a test is wrong, it should be deleted with a one-line rationale, not skipped silently.

Max 2 fix attempts per failure. Don't pursue beyond that without checking in.

## Step 4 — Build

Run a production build from a clean state. If the project has known cache pitfalls (`.next/`, `dist/`, `.turbo/`), clear them before this step on a final pre-deploy run.

If the build fails after type-check and lint passed, the failure is usually env vars, build-time data fetching, or framework-specific config — surface the actual build error verbatim, don't paraphrase.

## Step 5 — E2E (conditional)

Run E2E only if:
- A test:e2e script exists, AND
- The project's documented preconditions for running E2E are met (env var gates, local test DB, browser available)

If preconditions aren't met, report `E2E SKIPPED — <specific reason>`. Do not silently omit. Do not run E2E against the production database without an explicit allow-flag — most projects gate this.

Max 1 fix attempt on a flaky test; if it fails twice, flag it as flaky and continue. Don't burn budget chasing flakiness.

## Step 6 — Hygiene checks (read-only)

In files changed since the last commit:
- `console.log` / `console.error` / `debugger` introduced.
- `TODO` / `FIXME` / `XXX` added.
- Stray `.only` / `.skip` on tests.

Surface as warnings, not failures.

## Final report

Always structured as:

```
TYPE CHECK   — PASS / FAIL / SKIPPED (reason)
LINT         — PASS / FAIL / NOT CONFIGURED
UNIT TESTS   — PASS (N tests) / FAIL (N failing) / NOT CONFIGURED
BUILD        — PASS / FAIL (one-line summary of error)
E2E          — PASS (N tests) / FAIL / SKIPPED (reason)
HYGIENE      — clean / N warnings
```

End with:
- **ALL PASS** — green light
- **FAIL** — list which steps failed and the unresolved issue from each
- **PARTIAL** — some steps couldn't run (E2E skipped, lint not configured); name each

Never report success while having silently skipped a step. If you skipped, say so.
