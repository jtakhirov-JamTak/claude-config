# Reviewer Conventions

Lives at `~/.claude/REVIEWER_CONVENTIONS.md` — user-global, so every project picks it up with no per-repo copy. Skills cite that path; keep the file here. A repo-local `.claude/REVIEWER_CONVENTIONS.md` shadows this one — don't create one. (`.claude/exceptions.md` is the opposite: genuinely per-repo, and stays repo-relative in every citation.)

Shared conventions for every skill that produces a severity-ranked review or audit. Applies to: `check-access`, `review-changes`, `grill`, `full-review`, `full-audit`, `deploy-check`, `mobile-check`, `privacy-audit`, `techdebt`, `ai-prompt-review`, `perf-check`, `a11y-check`, `observability-check`, `dep-audit`, `ci-check`, `db-check`. The built-in `/security-review` and the `staff-reviewer` subagent follow the same conventions when invoked inside `full-review`. (`test` is a generator/auditor hybrid — its `audit` mode follows the caps/scope conventions; its `write` mode produces code, not a ranked report.)

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
| `full-audit` | Whole repo (clean tree) |
| `a11y-check` | Pages touched by uncommitted changes |
| `perf-check` | Whole repo's hot paths (`surface=data\|bundle` to halve) |
| `ai-prompt-review` | Prompt + AI-output-schema files touched by uncommitted changes |
| `observability-check` | Whole repo's critical paths (`stage=prelaunch\|scaling` sets the bar) |
| `dep-audit` | Full dependency sweep (or one named package to vet) |
| `ci-check` | The repo's CI workflow (audit) or none (setup) |
| `db-check` | The most recent migration on disk (or a named migration / table) |
| `test` (`audit` mode) | Whole repo's risk surfaces |

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

- Write fixes inline with findings. A one-line "suggested direction" per finding is fine and expected (it's in most skills' output formats); the actual code change belongs in a follow-up pass so the user can review the diagnoses first.
- Add exceptions on the user's behalf. The user decides what's accepted.
- Re-flag the same finding the user has already declined in conversation history. If memory or prior in-session feedback contradicts a finding, surface that as a meta-note, not as a finding.
- Silently skip a category. If category 9 wasn't checked because the diff is backend-only, state that.
- Pad reports with LOW findings to look thorough. The default caps exist precisely to discourage this.

---

## 6. Canonical checks (cite by ID, don't restate)

These rules recur across several skills — reviewers and scaffolders both — and were previously copy-pasted verbatim (and drifted). Each skill now cites the ID with a one-line summary; the full mechanical detail lives here. **When you improve one of these rules, improve it HERE** — the citing commands inherit it. Adding a rule here while leaving the copies in place is worse than not extracting it: grep the ID's subject across `commands/` and replace every restatement with a citation.

### LINK-RESOLVE — internal navigation targets resolve to a real route

Extract every internal navigation target in or near the diff: `href="..."`, `<Link href="...">`, `router.push(...)`, `router.replace(...)`, `redirect(...)`, and any route constant/map (`MODULE_TO_PATH`-style). For each, confirm a matching page exists on disk — don't eyeball, resolve it. Next.js App Router: drop route-group `(group)` segments from the path and match `[param]` / `[...slug]` dynamics; other routers resolve against their route table. A target with no matching route is a **live 404 → HIGH**. A link to a *deleted* page is the most common instance and usually lives in a file the diff didn't touch — so resolve links in the surrounding files too, not just changed lines.

### GATE-PRESERVE — a gated submit must not discard the user's input

A multi-step or expensive-to-fill form that hits a 403 / paywall / auth-required on submit must NOT hard-`router.push(...)` / `redirect(...)` away and discard what the user typed. A redirect technically "offers a next action," so it passes a generic error-path check — verify this one *separately*. The gate response should keep the form mounted, snapshot any prior output, and inline the upgrade prompt. Construct the case: user fills the whole form, endpoint returns 403 — is their work still on screen afterward, or gone? Abandoning a filled form at the exact pay moment is the highest-friction conversion failure → **HIGH**.

### DB-ERROR-CHECK — inspect `.error` on every DB call

Clients that return `{ data, error }` (PostgREST/Supabase `maybeSingle()`, bare `.select()`, `.upsert()`, `.update()`, fire-and-forget writes) do NOT throw on RLS misconfig, schema drift, or transient outage — they return the error in the value, and a `try/catch` won't catch it. Every such call needs `const { error } = await …; if (error) capture/return`. `Promise.all` over writes hides per-row failures — collect results and inspect each. Missing this renders the empty/zero state with no error signal, so the user concludes their data is gone → **HIGH**.

### VERSION-GUARD — bump the version symmetrically when a stored shape changes

When code that computes a stored snapshot (a derived row, a cached `jsonb` blob, an AI output) changes the **shape** of what it writes (field added/removed/renamed/retyped), the version stamp must bump on BOTH sides: the code-side constant (`PROMPT_VERSION`/`GENERATOR_VERSION`) AND the DB-side column (`generator_version`/`ai_*_version`) the row carries. Reader and writer must filter on that version the same way — if the reader gates on `row.version === CURRENT` but the writer's cache-lookup doesn't, stale rows loop forever; if the writer bumps but the reader doesn't, new-shape rows render as garbage under old-shape code. Fall all-or-nothing per version: a mismatched row triggers live recompute, never a mixed render. A code-side bump with the DB column left untouched is traceability theater — old and new rows become indistinguishable → **HIGH**.

### VERIFY-GATE — run the project's verification gate, discovered not assumed

Run the project's verification gate, discovered from `package.json` — never assume a script name. Use `npm run verify` if it exists; otherwise run the project's own equivalents in order: type check (`typecheck` / `check` / `tsc --noEmit`) → lint → unit tests → production build, stopping on the first failure. State which form you used, and report each step as ran / skipped / failed. Where a `verify` script exists, don't re-implement the sequence — the script owns it. A repo with no single verify script is a gap worth noting once, not a failure.

Callers add their own two clauses: whether to build from a **clean state** (clear `.next`/`dist`/`.turbo` — yes for a final pre-deploy pass or a whole-repo fan-out, no for a quick diff pass), and what a failure **stops** (the review pipeline, the audit fan-out, the deploy). CI must run these same steps — see `ci-check`; local and CI drifting apart defeats the point of a single gate.

### GATE-EXCLUSIONS — routes that must NOT carry the paywall/access gate

The same five routes are wrongly gated over and over. Gating any of them breaks a first-touch or money path silently, because the failure is a 403 nobody sees:

- **Auth callback / session refresh** — gating it locks users out of their own session.
- **The endpoint that _creates_ the subscription** — gating the thing you buy access with is a deadlock.
- **Onboarding writes that run before the user can pay** — pre-payment writes must land or the user can never reach the paywall.
- **Webhook receivers** — called by a provider, not a session; their trust boundary is the signature. A gated webhook 403s the provider and entitlements silently never apply.
- **Admin routes** — use the admin helper, not the paid gate.

Both directions are findings: a route in this list that IS gated (breaks the flow), and a route outside it that ISN'T (bypass). Auditors flag both; scaffolders must not emit a gate on any of the five.

### MOBILE-FLOOR — the non-negotiable mobile baseline

The floor every user-facing page meets, enforced at scaffold time and audited by `mobile-check`:

- **Input font-size ≥ 16px** — iOS Safari zooms on focus below 16px and silently breaks the form.
- **Tap targets ≥ 44pt (iOS) / 48dp (Android)** on the tappable axis; wrap native checkboxes in a `<label>` with `min-h-11` so the row is the target. (WCAG AA's own floor is only 24×24 CSS px — `a11y-check` cites that lower bar for conformance; this one is the product bar.)
- **Contrast ≥ 4.5:1 body, ≥ 3:1 large/decorative.** The default mid-grey utilities (`text-zinc-400`, `text-gray-400`) fail AA at small sizes — go one or two shades darker.
- **Horizontal padding ≥ 16px** from the viewport edges.
- **Reserve bottom space for a fixed tab bar** — otherwise the last card sits behind it, partially tappable.

These five numbers are maintained HERE. `mobile-check` audits against them and owns the rest of the device surface (soft-keyboard occlusion, viewport, PWA, interaction traps); `a11y-check` owns the assistive-tech surface and cites WCAG's lower 24x24 target bar deliberately, not by mistake. Scaffolders and auditors alike cite this floor; nobody restates it. If the project's existing pages violate the floor, match the floor, not the siblings.

### DISCOVER-FIRST — find the project's existing helpers before scaffolding or judging

Skip this and you will recommend abstractions that already exist under a different name, or invent a pattern the codebase has already rejected. Read `package.json`, then locate:

| What | Where it usually lives / search terms |
| --- | --- |
| Framework + router | `src/app/`, `pages/`, `routes/`, `src/routes/` |
| Validation library + schemas | `validation`, `schemas`, `zod`, `valibot` |
| AI output schemas (if AI) | `ai/schemas`, `prompts`, `llm` |
| Auth helper | `getAuthUser`, `requireUser`, `getServerSession` |
| CSRF / origin helper | `checkOrigin`, `verifyCsrf`, `sameOrigin` |
| Rate-limit helper | `rateLimit`, `limiter`, `throttle` |
| Access gate helper(s) | `requirePaidAccess`, `requireAccess`, `checkSubscription` |
| Idempotency | `idempotencyKey`, `dedupe`, `requestId` |
| Migration tool | `supabase/migrations/`, `prisma/migrations/`, `drizzle/`, flyway, dbmate |
| Generated DB types | `types/database.ts`, `db/schema.ts`, or wherever the regen lands |
| Authorization model | RLS policies vs app-level middleware vs RBAC table |
| Styling system | Tailwind, CSS Modules, styled-components, vanilla |

**Read one nearby existing example end-to-end. That is the template.** Match its shape unless there's a deliberate, named reason not to. Reviewers apply the same rule in reverse: don't flag a missing helper without first checking whether the project has one — "should use the rate limiter" is noise in a repo with no rate limiter, and the architectural gap is the separate, larger finding.

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

### ERROR-SINK-SCRUB — the error tracker's default configuration leaks user content

An error sink (Sentry and equivalents) ships with a config that sends more than the stack trace to a third party. Three surfaces, in the order they get missed:

- **`event.exception.values[*].value`.** SDK error messages are built from the HTTP *response* body, and that body routinely carries data. A PostgREST/Supabase conflict error returns `Key (user_id, name)=(…) already exists` — real column values, in the message. Scrub-spec tutorials cover `request.data` and `extra` and stop there. Redact every `ex.value` in a shared `scrubEvent`, or wrap at the capture site with a synthetic `new Error("short_tag")`. Do **not** assume a given SDK echoes your *request* body — verify against a real captured event before writing that into a project's rules.
- **Breadcrumbs.** These do reach `beforeSend` as `event.breadcrumbs`, so scrubbing them there is possible — it just never happens, because the scrubber gets written against the exception and nobody revisits it. Use `beforeBreadcrumb` instead: it filters at capture time, before a console breadcrumb has stringified a raw error or a fetch breadcrumb has recorded a URL with a `?q=` search term in it. Configure it in the same change that enables the DSN, not after.
- **Transactions/traces genuinely do bypass `beforeSend`** — they run through `beforeSendTransaction`. Traces carry full URL, query, and route metadata, and can't be scrubbed retroactively. `tracesSampleRate: 0` until a tracing consumer actually exists.

Operational half: **latch any capture on a per-request path behind a cooldown.** A `captureException` inside a fallback catch that's hit on every request fires thousands of times a minute during an outage, exhausts the event quota, and the alert that would have named the outage never fires — observability failing exactly when it's needed. Module-level `Map<kind, lastCaptureAt>` with a 5-minute per-kind cooldown.

Leaked user content at a third party can't be recalled → **HIGH**, or **CRITICAL** where the payload is sensitive personal content.

### MIGRATION-PREFLIGHT — a structural migration must defend against the rows already there

Local checks pass because they run against a clean or synthetic database. Production has history. Four forms:

- **Unique index on a column that isn't unique yet.** `CREATE UNIQUE INDEX` aborts the whole migration on the first duplicate. Two acceptable resolutions, and the choice must be deliberate: (a) **fail loudly** — pre-flight `SELECT` the conflicting keys and abort with them named, so an operator decides; or (b) dedup with an **explicit, documented survivor rule** (most-complete row, most recent activity — not `ORDER BY id`, which silently keeps the oldest for no stated reason). A blind `DELETE … WHERE rn > 1` is destructive data loss chosen by accident; never emit one as the default.
- **`NOT NULL` / new `CHECK` on an existing column.** Backfill first, in the same migration.
- **A new value written into a *reused* column.** Read the live constraint first (`pg_get_constraintdef` over `pg_constraint`) — this is uniquely nasty because type-checking and unit tests both pass: they exercise the schema and the field mapping, never a live insert against the real constraint. The failure is a runtime 400, a cleanup path that deletes the raw row, and a generic "could not save" with nothing in the database. Then ask the prior question before reaching for a fix: **should that CHECK exist at all?** If the enum already lives in application code (Zod schema, TS union, const tuple), the CHECK is a second source of truth that drifts on the next rename — the durable answer is to drop it and let validation own the enum, or to generate it from the same source with a test asserting the two lists match. Widening the CHECK in the same migration (`drop constraint if exists` + re-add the superset) is the right move only when the constraint is genuinely DB-owned — ad-hoc SQL writers, external writers, policies that depend on it. Structural invariants (numeric ranges, timestamp ordering, array cardinality) are not enums and don't have this problem.
- **Timestamp-pair CHECKs.** `end > start` rejects a first-submit user whose two timestamps land equal. Use `>=`, or guarantee separation at write time.

### REDIRECT-VALIDATE — the post-auth return parameter is an open redirect

Any app with a login-then-return-here flow carries a `?next=` / `?returnTo=`. Accept only a same-origin relative path:

```
/^\/(?!\/)/.test(next) && !/[\\\x00-\x1f\x7f]/.test(next)
```

The backslash clause is the half that gets skipped: `\` is folded to `/` for http(s) URLs, so `/\evil.com` becomes `//evil.com` and walks through a leading-slash-only check. Control chars belong in the same reject for header and log injection. Equivalent and equally sound: `new URL(next, origin).origin === origin`, which inherits the same `\`-folding from the URL parser — wrap it in try/catch, since it throws on malformed input. Applies to every server-returned redirect value handed to a client-side navigation. Credential phishing against your own users → **HIGH**.

### READ-SURFACE-LIMITS — reads need caps, and the cookie/CORS config is what actually guards them

Reviewers skip GET handlers on the assumption that reads are safe. Two real controls and one common false one:

- **Per-day cap, not just per-minute.** 30 requests/minute reads as a reasonable limit and scrapes 43,200 records a day unnoticed. Any endpoint that enumerates user-scoped data needs a daily ceiling.
- **Every user-scoped query needs an explicit `.limit()`** — and know which of two failure modes you're in. Without a limit the query degrades silently as rows accumulate: fine at 10, crawling at 1000. With a limit above the client's own ceiling you get the worse one: PostgREST caps responses at 1000 rows by default and **silently truncates**, so an export or enumeration returns a plausible-looking partial answer. Raise `db-max-rows` deliberately or surface a truncation notice when the count equals the cap.
- **Do NOT add CSRF-style origin checks to read GETs.** They buy almost nothing and break real flows. A cross-site page's `fetch()` cannot read the response without CORS granting it, and `SameSite=Lax` — the browser default — doesn't send cookies on subresource requests, so the request arrives unauthenticated regardless. If the calling page is same-origin (XSS), an origin check is useless by definition. Meanwhile `Origin` is absent on same-origin navigations (`<a download>`, form submit, typed URL), so the check 403s every download button. The controls that actually guard the read surface are the cookie's `SameSite` attribute and a tight CORS allow-list — audit those two directly. (Origin checks remain correct and required on *mutating* endpoints — see the project's CSRF pattern.)

### FALLBACK-MASKS-FAILURE — a graceful read path can hide a broken write path indefinitely

The worst failure mode in a system isn't a crash, it's a feature that looks healthy while one layer of it has been dead for months. It needs two ingredients, and both are things a careful engineer adds on purpose:

1. A write that can fail **without throwing** — an INSERT rejected by a constraint, an upsert blocked by RLS, a cache row that never lands. `DB-ERROR-CHECK` covers inspecting `.error`; this check covers what happens next.
2. A read path that **falls through to live computation** when the row is missing — a legitimate availability pattern, and the thing that makes the failure invisible. The page renders correctly. Nobody files a bug. The cache is 100% empty and has been since the migration.

Both are individually good engineering. Together, with no signal in between, they produce a lie. The audit questions:

- Does every write on this path inspect its error **and** emit an operator signal (an error-sink capture with a distinguishing tag, not a log line nobody reads)? A write failure that only returns early is silent.
- When the read path takes the fallback branch, does *anything* record it? A fallback that fires 100% of the time and a fallback that fires 0.1% of the time must be distinguishable from the outside.
- Is the fallback visible to the **user** where it matters — a "regenerating", "last updated {date}", or stale-cache byline? A silent fallback trains everyone, including the operator, to believe the fast path works.
- Would a monitoring dashboard show the difference between "cache warm" and "cache never populated"? If the only way to find out is to query the table by hand, the answer is no.

Severity follows what the dead layer was for: a cache or derived table → **HIGH** (silently wrong data, unbounded duration); anything on a money, entitlement, or auth path → **CRITICAL**. This is a specific instance of `ENFORCED-NOT-INTENDED` — the invariant "the cache is populated" was intended everywhere and enforced nowhere.

### VACUOUS-PASS — a gate that measured nothing must fail, not pass

A green check has two possible meanings — "I looked and it was fine" and "I never looked" — and by default they are indistinguishable from the outside. Every gate must make the second meaning impossible to reach. The recurring instances: a test runner that exits 0 having discovered zero test files; a marker/grep assertion satisfied by the very artifact it was meant to reject; a report-consuming script that passes when the report directory is missing or empty; an assertion fed a sentinel instead of a measurement (`values.at(-1) ?? Infinity`); and a budget or threshold never calibrated against one real run, so it can only fire on a value nobody has ever observed. The audit questions: does the gate assert that it found something to measure **before** it asserts on the value? If you deleted the gate's input entirely, would it fail — or go green? Is the threshold traceable to a measured baseline, or invented? Retries make this worse rather than better: an intermittently red gate under `retries: 1` trains everyone to re-run instead of investigate, and the passing attempt reports a budget as met on evidence the first attempt never produced. Severity follows what the gate was protecting — a format/lint gate → **MEDIUM**; a test, migration, security, or performance gate → **HIGH**, because being the thing that noticed was the gate's entire purpose.

### PATTERN-REPEATS — one instance of a flaw is evidence of a class, not an incident

When a review, audit, or fix confirms one instance of a defect — a missing `.error` check, an ungated route, an unvalidated redirect, a PII column with no classification comment — do not close the finding at that instance. Derive the grep-able signature of the mistake and run it across the whole codebase **before** reporting. The instance you found was found by wherever attention happened to land; the rest are in the files nobody opened. Report the class with its full instance list and a count, not the single example — a finding that says "fix this line" gets that one line fixed and leaves the other six, which the next review then re-reports as new. Where the signature genuinely cannot be grepped (a judgment defect, an architectural mismatch), say so explicitly and name the surface that would have to be read by hand, rather than silently scoping the finding to its one visible instance. Severity is the severity of the **class**: the single instance's rating is a floor, never the ceiling.

---

## 7. Maintaining this set

The skills live in `~/.claude/commands/`; the agents in `~/.claude/agents/`. Read this before adding, renaming, or retiring one.

**Naming.** Scaffolders `add-<layer>` — five siblings, no router (the `add` router was retired 2026-08-18: its description told you to use the specific command instead, and its only unique content, the discover table, is now `DISCOVER-FIRST` in §6). New audits `<domain>-check`. Actions `<verb>` or `<verb>-<noun>`. Grandfathered, do NOT mass-rename: `check-access`, `privacy-audit`, `dep-audit`, `ai-prompt-review`, `review-changes` — they're cited by orchestrators and by this file, and the cosmetic gain is below the breakage risk.

**File shape.** Frontmatter (`name` matching the filename, one-line `description`) → purpose line + `$ARGUMENTS` → the 4-line reviewer-conventions block if it's a reviewer → Discover-first → steps/checks → Output with a severity ladder and a one-line verdict.

**Description rule.** One line: *what* + *when* + the NOT-clauses pointing at the neighbouring skill. Descriptions are always-loaded, so no check-list enumerations — those go in the body. The NOT-clauses are the triggering disambiguation; never drop one to save tokens.

**Adding a reviewer.** Add it to the roster and the default-scope table above, wire it into `full-review` / `full-audit` / `deploy-check` if it belongs in a pipeline, and give it the 4-line conventions block.

**Retiring anything.** Delete the file, then grep for dangling references — `full-review`, `full-audit`, `deploy-check`, the `add-*` scaffolders, the roster and scope table in this file, the §6 canonical checks, `~/.claude/CLAUDE.md`, `~/.claude/agents/`, and `/x` cross-refs inside other descriptions. This is LINK-RESOLVE applied to the skill set itself, and it is the step that actually gets skipped. An agent in `agents/` that nothing cites is dead weight — grep before assuming it's wired in.

**Never merge two skills** if it blurs a distinct trigger or drops a capability. Efficiency comes from trimming descriptions and sharing rules by reference, never from collapsing capabilities.

**Shell-neutral.** Machine and shell specifics live in `~/.claude/CLAUDE.md`, not in a skill. Where a skill must show a command the user will paste by hand (`commit`, `save-context`, `worktree`), show the PowerShell form beside the Bash one.

**Adopting the set in a new repo.** Skills are user-global — there is nothing to copy and no per-project install; `/…` commands already resolve in a fresh repo. Two things the repo must supply, because the skills read them and degrade quietly without them: a `CLAUDE.md` describing the stack and house rules (or run `/init`), and a `.claude/exceptions.md` from the template in §2. A repo missing `exceptions.md` has no way to record an accepted finding, so every reviewer run re-reports what the user already decided to live with — the failure looks like a noisy reviewer, not a missing file. Everything else is Discover-first's job: a different stack (Express/Drizzle vs Next/Supabase) needs no skill edits.

**Trigger-testing a new skill.** Before trusting a new or renamed skill, name three prompts that should fire it and three that should route to a neighbouring skill, then check the descriptions actually disambiguate those six. The NOT-clauses are the only triggering mechanism the set has, and nothing else verifies them. Do this in conversation — do not add a test block to the skill file; descriptions are always-loaded and the body is read on trigger, so a permanent fixture costs tokens on every session to document a one-time check.
