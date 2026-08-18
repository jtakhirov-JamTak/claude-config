---
name: grill
description: Adversarial pre-ship review of uncommitted changes — construct concrete inputs that BREAK the code, working a fixed failure-mode taxonomy. Use when you want attack scenarios with repro steps before committing. NOT routine line-by-line correctness/style (use /review-changes), NOT the multi-reviewer pipeline (use /full-review).
---

Adversarial review of uncommitted changes. The output is a list of plausible failure scenarios — not opinions, not vibes. Work the taxonomy below; for each category, *try to construct a concrete input or sequence that breaks the code*. If you can't construct one in 30 seconds, move on.

## Reviewer conventions (apply to this skill)

- **Scope**: `$ARGUMENTS` may name a file / dir / glob / symbol, or category names (e.g. `categories=1,3,5`) to limit which taxonomy categories run. Default scope is uncommitted changes, all categories.
- **Exceptions**: read `.claude/exceptions.md` at repo root before reporting; skip matching entries; surface any suppressed CRITICAL at the end.
- **Caps**: honor `top=N`, `critical-only`, `high-only`, `unbounded` in `$ARGUMENTS`. Default: at most 5 LOW + 10 MEDIUM listed individually, rest summarized.
- **Long-form rules**: `~/.claude/REVIEWER_CONVENTIONS.md`.

```
git diff --stat
git diff
```

## Taxonomy — work each category in order

### 1. Boundary and degenerate inputs
- Empty string, whitespace-only string, single character, exactly-at-limit length, length+1.
- `0`, `-0`, negative, `Number.MAX_SAFE_INTEGER + 1`, `NaN`, `Infinity`.
- Empty array, single element, duplicate elements, sort-violating order.
- Null, undefined, missing optional, present-but-empty.
- Unicode: emoji (multi-codepoint), zero-width joiner, RTL marks, combining characters, NUL byte, control characters.

### 2. Time and clock
- Operation invoked at exactly the same instant another wrote — `>` vs `>=` on timestamp checks.
- Server clock skew, daylight-savings transition, leap second.
- Cache window boundary: read at TTL-1ms, write at TTL+1ms.
- Timezone confusion: stored UTC, rendered local, compared mixed.

### 3. Concurrency and races
- Double-submit of the same form before the first response returns.
- React strict-mode double-mount fires effects twice (or any framework's dev-mode equivalent).
- Two tabs of the same user writing in parallel.
- Retry after partial success — does the second attempt observe state from the first?
- Idempotency: replay the same request, do you get the same outcome or a second row?

### 4. Auth and authorization
- Logged-out user hits the route directly.
- User A's session, request body carries user B's id — does it filter by the *authenticated* id?
- Expired or about-to-expire session token.
- Role/tier downgrade between when the page rendered and the action fires.
- CSRF: cross-origin POST from a malicious page using the user's cookies.
- Origin header absent (same-origin download, link click) — does the origin check fall back correctly?

### 5. Enumeration and exfiltration
- Compromised session running at 30 requests/minute for 24 hours — what gets scraped?
- Pagination boundary: page beyond last, page zero, page negative.
- Filter that's "any of" with an empty list — does it return everything?
- GET endpoint that lists user-scoped data: is there a per-day cap, not just per-minute?

### 6. Persistence failure modes
- DB call returns `{ data: null, error }` — is `.error` inspected? (**DB-ERROR-CHECK**, §6)
- `Promise.all` over writes — is each result checked, or does one silent failure get hidden?
- Cache delete succeeds, insert fails — does the user end up with an empty cache forever?
- Fire-and-forget write inside a try/catch — does `.error` actually throw, or just sit in the return value?
- UNIQUE constraint conflict on a retry — caught and treated as success, or surfaced as an error?

### 7. External service failure
- Upstream times out, returns 5xx, returns malformed body, returns a schema-valid but semantically wrong response.
- Rate limiter itself goes down — does the fallback fail-open (no protection) or fail-closed (lock users out)?
- AI returns whitespace, returns a category label instead of content, returns prose where JSON was expected, returns JSON wrapped in markdown.
- Per-request error capture during an upstream outage — does it exhaust the error sink quota?

### 8. UX and dead ends
- Action succeeds halfway (write OK, AI failed) — does the user land on a dead-end "Done" with no retry path?
- Empty state — is the copy specific, or does it read like a bug ("No data" with no next action)?
- Error state — does it offer a next action, or just "Try again later"?
- Loading state — buttons disabled, but is there a `useRef` guard so a fast double-tap doesn't sneak through?
- **Input destroyed at a gate.** Apply **GATE-PRESERVE** (`~/.claude/REVIEWER_CONVENTIONS.md` §6) as an adversarial case: fill the whole multi-step form, make the submit return 403 — is the user's work still on screen afterward, or did a hard `router.push(...)` / `redirect(...)` discard it? Check this *separately* from the empty/error-state bullets above — a redirect passes those but still loses the work.

### 9. Mobile-only
If the diff touches UI, run `/mobile-check` on the changed pages for the full mobile audit (targets, contrast, inputs, keyboard, PWA) rather than restating it here. Only construct mobile *break-it* scenarios this command is uniquely suited to: an async transcript firing against the wrong field because a sensor component isn't keyed by step; an outside-click dismiss on `mousedown` leaving a popover stuck on iOS Safari; a fast double-tap slipping past a `disabled`-only (no `useRef`) submit guard. If the diff is backend-only, state "category 9: N/A (no UI)".

### 10. Data confusion
- Two enum values with overlapping semantics — which wins where?
- Field renamed in DB, hand-typed row type in code didn't follow — silent miscompile becomes silent misrender.
- `null` vs `""` mixed between raw and derived storage — `IS NULL` queries miss the empty-string rows.
- Positional array encoding (`[negTag, posTag]`) where either can be absent — readers index wrong.

### 11. Link and route integrity (mechanical — don't eyeball, resolve)
Apply **LINK-RESOLVE** (`~/.claude/REVIEWER_CONVENTIONS.md` §6): extract every internal nav target near the diff (`href`, `<Link href>`, `router.push/replace`, `redirect`, route constants/maps) and resolve each against a real route on disk — App Router drops `(group)` segments and matches `[param]`. Any target with no matching route is a **live 404 → HIGH**. The most common instance is a link to a *deleted* page in a file the diff didn't touch, so resolve links in the surrounding files too.

### 12. Documented-but-unenforced assumptions (hunt OMISSION, not just commission)
The other 11 categories find *wrong code that's present*; this one finds *a safeguard that's absent* — the harder class, because there's nothing on screen to react to. Apply **ENFORCED-NOT-INTENDED** (`~/.claude/REVIEWER_CONVENTIONS.md` §6): for every invariant the code *states* (a "we assume…" / "callers guarantee…" / "card-only" comment, or a design that depends on one), find the line that actually ENFORCES it. If the only thing upholding it is a comment, a dashboard toggle, an env var, or human discipline, it's unenforced and can drift silently. Construct the break: the **producer-consumer gap** (the creation side never sets what the fulfillment side assumes — two correct files, one missing line) and the **out-of-repo control** (real enforcement lives in a dashboard/manual step the code can't see). A thorough reassuring comment *lowers* scrutiny — treat it as a flag, not a reassurance. Severity per what the invariant guards (money/auth/data → HIGH/CRITICAL).

## Output

For each scenario you constructed:

```
[CRITICAL|HIGH|MEDIUM|LOW] category — concrete input/sequence — observed/likely outcome — file:line
```

End with: total by severity. Verdict — `SHIP IT` (no HIGH/CRITICAL), `REWORK` (HIGH present, fixable), `DO NOT SHIP` (CRITICAL present).

If you found nothing in a category after honest effort, state "category N: clean" — that absence is itself information.

$ARGUMENTS
