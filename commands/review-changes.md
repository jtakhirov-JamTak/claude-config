---
name: review-changes
description: Severity-ranked correctness/consistency review of uncommitted changes — logic errors, helper-drift, missing .error checks, pattern mismatches, file:line findings. Use for a routine "review my diff" pass. NOT break-it scenarios (use /grill); NOT the full pipeline (use /full-review); NOT a fix (use /fix-bug). Prefer over the built-in /code-review for project-pattern-aware findings; use /code-review for a generic pass with --comment/--fix.
---

Code review of uncommitted changes. Output is severity-ranked with file:line references.

## Reviewer conventions (apply to this skill)

- **Scope**: `$ARGUMENTS` may name a file / dir / glob / symbol; default scope is uncommitted changes (`git diff`).
- **Exceptions**: read `.claude/exceptions.md` at repo root before reporting; skip matching entries; surface any suppressed CRITICAL at the end.
- **Caps**: honor `top=N`, `critical-only`, `high-only`, `unbounded` in `$ARGUMENTS`. Default: at most 5 LOW + 10 MEDIUM listed individually, rest summarized.
- **Long-form rules**: `~/.claude/REVIEWER_CONVENTIONS.md`.

## Step 0 — Read the diff

```
git diff --stat
git diff
```

Skim once for scope. If the diff is large, group changes by file family before reviewing (auth changes, schema changes, UI changes).

## Step 1 — Discover before judging

Apply **DISCOVER-FIRST** (`~/.claude/REVIEWER_CONVENTIONS.md` §6): for any change that calls a project helper (auth, gate, validation, rate limit, error sink), confirm the helper exists and is used per the existing convention, and find the nearest sibling doing the same thing — that sibling is the standard the change should match. Don't flag a missing helper the project doesn't have; that's a separate, larger architectural finding.

## Step 2 — Per-change checks

For each changed file:

### Correctness

- Logic errors: off-by-one, inverted conditions, wrong operator (`>` vs `>=` on timestamp comparisons is a recurring trap).
- Null and empty: how does this behave on `null`, `""`, `[]`, `undefined`? Whitespace-only strings pass truthy checks — `.trim()` before `.length`.
- Async: stale closures over state, missing `await`, unhandled rejection paths, double-fire under React strict mode or under retry.
- Error returns vs throws: apply **DB-ERROR-CHECK** (`~/.claude/REVIEWER_CONVENTIONS.md` §6) — `{ data, error }` calls don't throw on RLS/schema drift; every one needs `.error` inspection, and `Promise.all` over writes must collect + inspect each result.
- Link/route integrity (mechanical): apply **LINK-RESOLVE** (§6) — every internal target the change adds or touches resolves to a page that exists on disk; a dangling target is a live 404 → HIGH. Don't eyeball it; resolve each one.

### Security

- Auth check present at the entry of every new authenticated route.
- User-scoped queries filter by the authenticated principal id, not a client-provided value.
- Origin / CSRF check on mutating routes AND on enumeration GETs.
- Rate limits cover both per-minute and per-day for any expensive or sensitive endpoint.
- User text is delimited from instructions in AI prompts, not concatenated raw.
- New env vars accessed without a runtime guard will crash at runtime, not build time — `process.env.X!` patterns need a startup check.

### Data exposure

- Can this query return another user's row? If RLS is the only barrier, is it enabled and non-permissive?
- Are error messages or logs about to ship user content into the error sink? Cross-check the scrub config.

### Patterns / consistency

- Does this match how the nearest sibling does the same thing?
- Is the new abstraction earning its weight, or is it three lines pretending to be a framework?
- Does the change introduce a second source of truth for something the codebase already centralizes (gating, validation, formatting)?

### UX

- Loading and error states present.
- Error paths offer a next action.
- Expensive input survives a gate: apply **GATE-PRESERVE** (§6). A `router.push("/paywall")` in a submit handler "offers a next action" but still destroys the user's filled multi-step form — flag it HIGH separately from the loading/error-state bullets above.
- Mobile tap targets ≥ 44pt / 48dp; input font-size ≥ 16px.

### Simplicity

- Could a sibling helper be reused?
- Is the change reverting a pattern the codebase already converged on?

## Step 3 — Report

Severity-ranked:

- `CRITICAL` — paywall bypass, unauth access, cross-user data leak, data loss, irreversible action without confirmation.
- `HIGH` — silent failure paths, missing error handling on writes, divergence from a centralized helper.
- `MEDIUM` — missing rate cap, mobile tap-target failure, inconsistent pattern, missing index on a filterable column.
- `LOW` — naming, comments, dead branches.

For each finding: `file:line — one-line description — suggested change`.

End with: total by severity, and one-line verdict — `SHIP IT` / `NEEDS WORK (n CRITICAL, n HIGH)` / `STOP (CRITICAL)`. If `STOP`, name the specific blocker first.

$ARGUMENTS
