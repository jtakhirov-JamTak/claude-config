# Reviewer Conventions

Shared conventions for every skill that produces a severity-ranked review or audit. Applies to: `check-access`, `review-changes`, `grill`, `full-review`, `deploy-check`, `mobile-check`, `privacy-audit`, `techdebt`, `ai-prompt-review`, `perf-check`, `a11y-check`, `observability-check`, `dep-audit`, `ci-check`. The built-in `/security-review` and the `staff-reviewer` subagent follow the same conventions when invoked inside `full-review`. (`test` is a generator/auditor hybrid — its `audit` mode follows the caps/scope conventions; its `write` mode produces code, not a ranked report.)

Each affected skill inlines a compact 4-line summary of these rules. This file is the long-form reference for when the user wants to understand or change the conventions.

---

## 1. Scope

Every reviewer accepts a scope argument via `$ARGUMENTS`. Forms recognized:

- **File path** — `src/lib/auth.ts` — review that file only
- **Directory** — `src/app/api/coach/` — review files under that directory
- **Glob** — `src/**/*.ts` — review files matching the glob
- **Symbol** — `checkSubscription` — find files mentioning the symbol and review those

If no scope is provided, each skill uses its default scope:

| Skill | Default scope |
|---|---|
| `review-changes` | Uncommitted changes (`git diff`) |
| `grill` | Uncommitted changes |
| `full-review` | Uncommitted changes |
| `mobile-check` | Pages touched by uncommitted changes |
| `check-access` | All API routes |
| `privacy-audit` | Whole repo |
| `techdebt` | Whole repo |
| `deploy-check` | `scope=delta` (default): diff since last deploy. `scope=full`: whole repo |

State the resolved scope explicitly at the top of the report — "scoped to `src/app/api/coach/prepare/route.ts`", or "scoped to uncommitted changes (12 files)". Never run with an unstated scope assumption.

---

## 2. Exceptions

Before reporting any finding, read `.claude/exceptions.md` at the project root if it exists. Skip findings that match an entry.

### Format of `.claude/exceptions.md`

One exception per `###` heading block, each with explicit fields (this matches the template the project's `exceptions.md` ships with):

```
### <short title>
- **Scope:** file path / glob / route / symbol the exception applies to
- **Finding:** the specific check to skip (precise — don't blanket a whole category)
- **Severity:** the level the reviewer would otherwise assign (LOW/MEDIUM/HIGH/CRITICAL)
- **Why accepted:** the reason this is OK to ship as-is
- **Reviewed:** YYYY-MM-DD — revisit if the surrounding code changes
```

A finding matches an entry when both its file/area (Scope) and its description (Finding) fit. The `Reviewed` date stamps the acceptance — entries older than 180 days should be re-examined; the reviewer surfaces this at the end of the report ("3 exceptions are over 180 days old; consider reviewing them").

### How reviewers apply exceptions

1. For each finding, check whether the (file, finding-category) matches an exception entry.
2. If yes, **skip** the finding from the main report.
3. At the end of the report, surface a single line: "N findings suppressed by `.claude/exceptions.md` (M CRITICAL among them — listed below)". If any CRITICAL was suppressed, name each suppressed CRITICAL by one line so the user can verify the suppression is still intended.
4. Never suppress a finding silently with no surface.

### When to add an exception

When a finding is real but accepted — e.g. a webhook receiver legitimately skips CSRF because it uses signature verification; a health-check endpoint legitimately skips rate-limit because it must always respond. Adding the exception with a rationale and date is cheaper than re-explaining the deviation every audit.

When NOT to add an exception: to silence a finding you haven't actually evaluated. Exceptions decay into noise the moment they're used to dodge work.

---

## 3. Top-N and severity caps

Reviewers default to bounded output. Unbounded reports become noise.

### Default caps (no argument)

- At most 5 LOW findings listed; remaining LOW summarized as "plus N additional LOW findings".
- At most 10 MEDIUM findings listed; remaining MEDIUM summarized.
- All HIGH and CRITICAL findings listed individually.

### Argument overrides

- `top=N` — cap total output at N findings, ranked by severity then file order. `top=5` is the most common use.
- `critical-only` — only CRITICAL findings; everything else summarized as counts.
- `high-only` — CRITICAL + HIGH; MEDIUM and LOW summarized as counts.
- `unbounded` — disable caps; list everything. Use rarely.

### Ranking rule

When the cap forces truncation, rank by severity first (`CRITICAL > HIGH > MEDIUM > LOW`), then within severity by impact (data exposure > silent failure > defense-in-depth > style), then by file order.

### Severity inflation pressure

The reviewer should *force* itself to distinguish — not every concern is HIGH. Practical heuristic: at most 3 CRITICAL findings per review. If you have more than 3, you are either over-flagging or the project has a structural problem that should be one CRITICAL meta-finding plus its specifics as HIGH.

---

## 4. Reporting structure

Every reviewer ends its report with:

1. **Counts by severity** — `2 CRITICAL, 4 HIGH, 7 MEDIUM, 12 LOW`
2. **Scope** — repeat what was reviewed (file, dir, "uncommitted changes", etc.)
3. **Exceptions applied** — `N suppressed (M CRITICAL listed above)`
4. **Single highest-leverage fix** — one finding, named.
5. **Verdict** — skill-specific (`SHIP IT` / `NEEDS WORK` / `STOP` / `READY` / etc.)

This structure keeps reports comparable across reviewers and across runs.

---

## 5. What a reviewer should NOT do

- Propose fixes inline with findings. Findings are diagnoses; fixes belong in a follow-up pass so the user can review the diagnoses first.
- Add exceptions on the user's behalf. The user decides what's accepted.
- Re-flag the same finding the user has already declined in conversation history. If memory or prior in-session feedback contradicts a finding, surface that as a meta-note, not as a finding.
- Silently skip a category. If category 9 wasn't checked because the diff is backend-only, state that.
- Pad reports with LOW findings to look thorough. The default caps exist precisely to discourage this.

---

## 6. Canonical checks (cite by ID, don't restate)

These rules recur across several reviewers and were previously copy-pasted verbatim (and drifted). Each reviewer now cites the ID with a one-line summary; the full mechanical detail lives here. **When you improve one of these rules, improve it HERE** — the citing commands inherit it.

### LINK-RESOLVE — internal navigation targets resolve to a real route

Extract every internal navigation target in or near the diff: `href="..."`, `<Link href="...">`, `router.push(...)`, `router.replace(...)`, `redirect(...)`, and any route constant/map (`MODULE_TO_PATH`-style). For each, confirm a matching page exists on disk — don't eyeball, resolve it. Next.js App Router: drop route-group `(group)` segments from the path and match `[param]` / `[...slug]` dynamics; other routers resolve against their route table. A target with no matching route is a **live 404 → HIGH**. A link to a *deleted* page is the most common instance and usually lives in a file the diff didn't touch — so resolve links in the surrounding files too, not just changed lines.

### GATE-PRESERVE — a gated submit must not discard the user's input

A multi-step or expensive-to-fill form that hits a 403 / paywall / auth-required on submit must NOT hard-`router.push(...)` / `redirect(...)` away and discard what the user typed. A redirect technically "offers a next action," so it passes a generic error-path check — verify this one *separately*. The gate response should keep the form mounted, snapshot any prior output, and inline the upgrade prompt. Construct the case: user fills the whole form, endpoint returns 403 — is their work still on screen afterward, or gone? Abandoning a filled form at the exact pay moment is the highest-friction conversion failure → **HIGH**.

### DB-ERROR-CHECK — inspect `.error` on every DB call

Clients that return `{ data, error }` (PostgREST/Supabase `maybeSingle()`, bare `.select()`, `.upsert()`, `.update()`, fire-and-forget writes) do NOT throw on RLS misconfig, schema drift, or transient outage — they return the error in the value, and a `try/catch` won't catch it. Every such call needs `const { error } = await …; if (error) capture/return`. `Promise.all` over writes hides per-row failures — collect results and inspect each. Missing this renders the empty/zero state with no error signal, so the user concludes their data is gone → **HIGH**.

### VERSION-GUARD — bump the version symmetrically when a stored shape changes

When code that computes a stored snapshot (a derived row, a cached `jsonb` blob, an AI output) changes the **shape** of what it writes (field added/removed/renamed/retyped), the version stamp must bump on BOTH sides: the code-side constant (`PROMPT_VERSION`/`GENERATOR_VERSION`) AND the DB-side column (`generator_version`/`ai_*_version`) the row carries. Reader and writer must filter on that version the same way — if the reader gates on `row.version === CURRENT` but the writer's cache-lookup doesn't, stale rows loop forever; if the writer bumps but the reader doesn't, new-shape rows render as garbage under old-shape code. Fall all-or-nothing per version: a mismatched row triggers live recompute, never a mixed render. A code-side bump with the DB column left untouched is traceability theater — old and new rows become indistinguishable → **HIGH**.

### ENFORCED-NOT-INTENDED — an invariant must be enforced by code that can't silently drift, not merely documented or configured

The cross-cutting one. Reviews reliably catch **commission** (wrong code that's present) and reliably MISS **omission** (a safeguard that's absent). The miss has a signature: a comment or design *states* an invariant ("card-only", "callers guarantee non-null", "PII is scrubbed", "capped at 1000 rows") while nothing in code actually *guarantees* it — and the reassuring comment LOWERS scrutiny because it reads as "handled." So for every assumption you can name in the code under review, find the line that ENFORCES it. If the only thing upholding it is (a) a comment, (b) a provider/dashboard toggle, (c) an env var or build-time convention, or (d) human discipline ("remember to bump the version"), treat it as **unenforced** — it can drift without a code change and without a failing test. Two recurring shapes:
- **Producer–consumer gap** — the consumer/fulfillment side assumes a property the producer/creation side never sets: two individually-correct files with a missing line between them. Check the producer enforces what the consumer assumes.
- **Out-of-repo control** — the real enforcement lives where the code can't see it (dashboard, manual ops step), so from the code's standpoint it's absent and driftable.

Apply through each domain's lens (same rule, different surface):
- **access** — an RLS *policy* exists but `ENABLE ROW LEVEL SECURITY` was never run (dead policy, open table); a route assumes middleware already authed it but the matcher excludes its path.
- **privacy** — "PII scrubbed in `beforeSend`" while `beforeBreadcrumb` still leaks it; deletion assumes every table cascades but a newer table has no cascade FK (verify on the **live DB**, not the migration files).
- **payments** — `payment_method_types` left unset, so "card-only" lives in the Stripe dashboard, not code.
- **observability** — errors are *captured* but no *alert* routes them to a human: capture documented, paging unenforced.
- **perf** — a `.limit()` cap assumed but dropped in a refactor; an index the query needs that the migration never applied; a provider row-cap (`db-max-rows`) that silently truncates.
- **AI** — "user content is delimited from instructions" until a new field bypasses the delimiter; "output validated" while the banned-phrase walker skips nested array fields.

Severity tracks what the unenforced invariant guards: money / auth / data-exposure → **HIGH/CRITICAL**; correctness / perf → **MEDIUM**. (`VERSION-GUARD` above is a specific instance of this rule — the version bump documented but not enforced symmetrically.)
