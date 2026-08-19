---
name: full-review
description: Run the full review pipeline on uncommitted changes — verification, adversarial, security, architecture, performance/mobile/accessibility/privacy (each when relevant) — and offer to fix. Use before committing a substantial diff. NOT a whole-repo sweep on a clean tree (use /full-audit); NOT the ship gate (use /deploy-check); NOT a single quick diff pass (use /review-changes).
---

Run the full review pipeline on uncommitted changes. Each step is conditional — skip categories that don't apply to this diff. Stop the pipeline on any verification failure; reviewing code that doesn't compile is wasted work.

## Reviewer conventions (apply to this skill and propagated to every sub-step)

- **Scope**: `$ARGUMENTS` may name a file / dir / glob to scope the entire pipeline; default scope is uncommitted changes. The scope propagates to every sub-step.
- **Exceptions**: each sub-step reads `.claude/exceptions.md`; the consolidated report at the end surfaces total suppressed across all steps and lists any suppressed CRITICAL once.
- **Caps**: honor `top=N`, `critical-only`, `high-only`, `unbounded` in `$ARGUMENTS`. The cap applies to the _consolidated_ report, not per sub-step — duplicate findings across reviewers are collapsed before the cap is applied.
- **Long-form rules**: `~/.claude/REVIEWER_CONVENTIONS.md`.

## Step 0 — Triage the diff

```
git diff --stat
```

Classify the changes:

- **UI/page changes** → mobile-check AND a11y-check apply
- **API route / handler changes** → security review applies
- **DB / schema / migration changes** → schema-specific review applies (cascade, RLS, constraints, indexes)
- **New/changed queries, large reads, or client-bundle additions** → perf-check applies
- **AI prompt / model config changes** → prompt-and-output-shape review applies
- **Data-flow changes (new field collected, new provider called)** → privacy-audit applies
- **Backend-only refactor with no behaviour change** → most categories don't apply; verification + simplifier may be enough

Note which categories you're running and which you're skipping with one-line rationale.

## Step 1 — Verification (always)

Apply **VERIFY-GATE** (`~/.claude/REVIEWER_CONVENTIONS.md` §6) — discover the gate from `package.json`, never assume a script name. No clean-state rebuild needed for a diff pass. If any step fails, **stop the pipeline** — reviewing code that doesn't compile is wasted work.

## Step 2 — Simplifier pass (always, unless diff is trivial)

Run `/simplify` (built-in) — surface any new code that's verbose, over-abstracted, or re-derived from a sibling helper that already exists. Don't fix yet; just collect findings.

## Step 3 — Adversarial review (always)

Run `/grill`. Work the taxonomy. Output: severity-ranked failure scenarios.

## Step 4 — Code review (always)

Run `/review-changes`. Output: severity-ranked correctness / pattern / consistency findings.

## Step 5 — Security review (conditional — if any API, auth, schema, or data-flow change)

Run `/security-review` (built-in). Check: auth at entry, user-id filtering, origin check, rate-limit (per-min AND per-day), schema validation, sensitive-data exposure, AI prompt injection delimiting, secrets.

## Step 5b — AI-prompt review (conditional — if any AI prompt, output schema, or model-config change)

Run `/ai-prompt-review` on the changed prompt/schema files. Check: user-text delimited from instructions, output schema present with `.trim().min(1)` + `.max()` caps, banned-phrase walker covers nested array-of-object fields, `PROMPT_VERSION` + DB `generator_version` bumped on any output-shape change. This is the surface Step 5's generic security pass doesn't know your discipline for.

## Step 6 — Architecture review (conditional — if the diff introduces a new abstraction, helper, table, or cross-module dependency)

Launch the staff-reviewer-style critique. Question whether the new abstraction earns its weight, whether it duplicates a centralized helper, whether the data model holds up at expected scale.

## Step 6b — Performance check (conditional — new/changed queries, large reads, or client-bundle additions)

Run `/perf-check` scoped to the changed surface. Look for N+1, unbounded reads, missing indexes on newly-filtered columns, and heavy deps added to the client bundle. Skip if the diff touches no queries and adds no client dependencies.

## Step 7 — Mobile check (conditional — UI/page changes only)

Run `/mobile-check` on the changed pages. Skip if the diff is backend-only.

## Step 7b — Accessibility check (conditional — UI/page changes only)

Run `/a11y-check` on the changed pages — keyboard operability, semantics, labels, focus, status announcements. Complements mobile-check (device) with the assistive-tech surface. Skip if the diff is backend-only.

## Step 8 — Privacy spot-check (conditional — new field collected, new provider called, or change to error-sink/logging code)

Run `/privacy-audit` scoped to the changed surface. Look specifically at: new PII columns, new sub-processors, error-sink scrubbing of new error paths.

## Step 9 — Consolidate

Merge findings from all steps, deduplicating across reviewers (Grill and review-changes will often surface the same issue from different angles — keep the more specific one).

Group by severity:

- `CRITICAL` — ship blockers
- `HIGH` — silent failure, drift from helper, gate bypass
- `MEDIUM` — defense-in-depth gaps, mobile fails, missing index
- `LOW` — style, naming, dead branches

For each: source-step / file:line / one-line / suggested fix.

## Step 10 — Verdict

- `READY TO SHIP` — no CRITICAL or HIGH
- `NEEDS WORK` — list HIGH/CRITICAL by number
- `STOP — VERIFICATION FAILED` if step 1 didn't pass

## Step 11 — Offer to fix

If `NEEDS WORK`, ask the user: "Which numbered findings should I fix? Reply with numbers, 'all CRITICAL', or 'all'."

For each picked item:

1. Run `/fix-bug` on it.
2. Re-run only the step(s) that originally surfaced the finding.
3. Confirm the fix; move to the next.

Don't re-run the whole pipeline after each fix — that's wasted work. Only re-verify at the end if multiple fixes shipped.

$ARGUMENTS
