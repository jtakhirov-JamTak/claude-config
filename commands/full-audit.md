---
name: full-audit
description: Whole-repo periodic health sweep — fans out ALL audit skills as parallel agents, finishes with live-DB verification, then produces ONE deduplicated severity-ranked backlog. Use for a scheduled "audit everything" pass on a clean tree. NOT a diff review (use /full-review); NOT a single ship gate (use /deploy-check).
---

Whole-repo audit orchestrator. Runs the full battery of audits in the most effective order, deduplicates their overlapping findings, and ends with a single triaged backlog + go/no-go.

This is the periodic "is the whole app healthy" sweep. It operates on the **whole repo**, not a diff — the diff-scoped reviewers (`/review-changes`, `/grill`, `/full-review`, the built-in `/code-review`, `/security-review`) do nothing useful here on a clean tree.

## Why this skill exists (read before editing it)

Running `/deploy-check scope=full` is NOT equivalent to running this. `deploy-check` folds the sub-audits in _by prose reference_ and skims — in practice it misses what the dedicated skills catch (dependency CVEs, the missing focus indicator, the silent-failure observability gaps). This skill fixes that failure mode by **spawning each audit as its own agent that actually runs the skill**, then synthesizing. Do not "optimize" it back into a single by-reference pass.

Two structural facts this skill encodes:

1. **The whole code-level suite is blind to live DB state.** Every audit infers schema/RLS/migration-applied from the repo. `/db-check` against the live database is the mandatory final step, not optional.
2. **Genuine cross-skill overlap is small.** The only real duplication is deploy-check ∩ privacy-audit on _account-deletion / privacy-policy / data-export_. The webhook and auth-callback get touched by several skills, but each examines a _different property_ (correct vs untested vs unalerted vs access-safe) — that's coverage, keep it. The synthesis step dedups the former and preserves the latter.

## How to run it

### Phase 0 — Verification gate (do first, inline)

Apply **VERIFY-GATE** (`~/.claude/REVIEWER_CONVENTIONS.md` §6) — discover the gate from `package.json`, never assume a script name. Build from a **clean state**: clear `.next`/`dist`/`.turbo` first. If it FAILs, report the failure and **stop** — auditing a repo that doesn't build wastes the fan-out. Don't proceed to Phase 1 until green (or the user explicitly says audit-anyway).

### Phase 1 — Fan out ALL audits as parallel agents (single message, multiple Agent calls)

Dispatch these as **concurrent** general-purpose agents. Every agent prompt must say: **REPORT ONLY — no edits, no fixes, no commits**; and must return a structured block: `SKILL / FOCUS / FINDINGS (severity + file:line) / BLIND SPOTS / COUNT`. Pass `scope=full`/whole-repo where the skill takes it.

1. `/check-access` — auth, user-id filtering, origin, rate-limit, RLS-in-code, gate drift
2. `/privacy-audit` — PII inventory, deletion cascade, export, sub-processors, error-sink scrub
3. `/perf-check` — N+1, unbounded reads, indexes, bundle weight
4. `/dep-audit` — CVEs, lockfile, license, typosquat ← **unique coverage, nothing else finds CVEs**
5. `/techdebt` — dead code/UI/exports, duplication, stale copy (scan only, do NOT approve fixes)
6. `/test` `audit` — undertested high-risk surfaces (money/auth/derived/migrations)
7. `/observability-check` — critical-path signal, error-sink latching, alerts on money/auth/AI-spend ← **unique: "will it page us"**
8. `/a11y-check` — screen-reader/keyboard/semantics/WCAG AA (name the key user-facing pages)
9. `/mobile-check` — touch targets, contrast, soft-keyboard, viewport, PWA manifest (name the key pages)
10. **Launch-residue agent** (the deploy-check-only slice, so we don't re-skim): secrets in client bundle, source maps, kill switches, payment lifecycle (money never client-granted, webhook sig + idempotency), legal-pages presence, open-redirect. Tell it to SKIP anything owned by skills 1–9 above (it is the residue, not a second pass).

Run a11y and mobile as separate agents — they share a "contrast not measured" blind spot but otherwise cover disjoint ground (assistive-tech vs device).

### Phase 2 — Live DB verification (after Phase 1 returns)

Run `/db-check` against the live Supabase target. This is the one thing no Phase-1 agent can see. If the user hasn't confirmed it's safe to query live, ask first. Parse the latest migrations for expected schema objects and verify they're actually applied (the recurring "column does not exist in prod despite migration ran" class).

### Phase 3 — Synthesize ONE backlog

Collect all returns and produce:

- **Deduplicated findings table**, severity-ranked. Merge the deletion/policy/export trio (deploy-residue ∩ privacy-audit) into single rows — privacy-audit's framing wins, note both flagged it. Keep the webhook/auth-callback multi-skill findings as _separate_ rows (different properties).
- **Unique-coverage callouts**: which findings only ONE skill caught (these justify keeping each skill).
- **Collective blind spots**: what the whole suite still can't see (live-DB beyond db-check's checks, runtime/rendered behavior, measured contrast, vendor dashboard config like Sentry alert rules and AI-vendor training opt-out — these need a human).
- **Triaged action buckets**: (A) safe code fixes, (B) bigger code work, (C) founder-must-do (legal text, dashboard config, vendor toggles), (D) features needing a design decision.
- **Single go/no-go** for launch + highest-leverage fix + longest-lead-time fix.

## Caps & conventions

- Honor `top=N` / `critical-only` / `high-only` in `$ARGUMENTS`.
- Read `.claude/exceptions.md` first; skip matching entries; surface any suppressed CRITICAL at the end.
- Long-form rules: `~/.claude/REVIEWER_CONVENTIONS.md` — pass the same conventions down to every dispatched agent.
- This skill DISPATCHES and SYNTHESIZES — it does not itself fix. Offer to hand the backlog to a fix pass at the end; don't auto-fix.
- Token cost is real (10+ full-repo agents). State that up front so it's not a surprise; it's the intended cost of a periodic full sweep.

$ARGUMENTS
