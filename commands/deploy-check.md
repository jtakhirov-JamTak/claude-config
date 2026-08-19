---
name: deploy-check
description: Deployment audit — `scope=delta` (default) for since-last-deploy risk review; `scope=full` for whole-repo launch readiness. Use as the ship gate, before and after rollout. NOT a review of uncommitted changes (use /full-review); NOT the periodic whole-repo health sweep (use /full-audit).
---

Pre-deploy or pre-launch audit. Argument-driven scope:

- `/deploy-check` — `scope=delta`, since-last-deploy risk review (default; what you run before every deploy)
- `/deploy-check scope=full` — whole-repo launch readiness (what you run before public launch / major milestones)
- `/deploy-check target=staging` — same checks, staging risk tolerance
- `/deploy-check target=prod` — prod risk tolerance (default)

## Reviewer conventions (apply to this skill)

- **Scope**: `$ARGUMENTS` parses `scope=delta|full`, `target=staging|prod`, `base=<sha>` (override the auto-detected last deploy).
- **Exceptions**: read `.claude/exceptions.md` at repo root before reporting; skip matching entries; surface any suppressed BLOCKER at the end.
- **Caps**: honor `top=N`, `critical-only` (BLOCKERs only), `high-only` (BLOCKERs + RISKs), `unbounded` in `$ARGUMENTS`. Default delta: list every BLOCKER and RISK individually; cap WATCH at 5. Default full: list every CRITICAL and IMPORTANT; cap NICE-TO-HAVE at 5.
- **Long-form rules**: `~/.claude/REVIEWER_CONVENTIONS.md`.

---

# Verification (always — both scopes)

Apply **VERIFY-GATE** (`~/.claude/REVIEWER_CONVENTIONS.md` §6) — discover the gate from `package.json`, never assume a script name. For a final pre-deploy pass, build from a **clean state**: clear `.next`/`dist`/`.turbo` first. Report each step as ran / skipped / failed. If any step fails, **stop and do not deploy.**

A repo with no single verify script is not a pass — it's a gap. Note it once in the report (`RISK`: no single local verification gate; consider adding a `verify` script) and continue with the discovered sequence.

Apply **VACUOUS-PASS** (`~/.claude/REVIEWER_CONVENTIONS.md` §6) to the gate itself before trusting it green: a step that exits 0 having measured nothing is the one failure a verification pass cannot catch by re-running it. For each step ask whether deleting its input would fail it or green it. A false green here ships.

---

# `scope=delta` — since-last-deploy risk review

The job: surface what's _risky about this specific deploy_. Not a re-audit of the whole app.

## Find the last deploy

```
git log --oneline -20
```

Identify the commit last deployed. If unclear (no deploy tags, no CI history), ask the user, or accept `base=<sha>` from args.

```
git diff <base>..HEAD --stat
git diff <base>..HEAD
```

## Migration risk

For every migration added since last deploy:

- Idempotent? Re-running on an already-migrated DB should be safe.
- Dedup CTE before any new UNIQUE index?
- Backfill before any new NOT NULL or CHECK?
- `>` where `>=` is safer on timestamp pairs?
- RLS enabled and non-permissive on every new table?
- Generated DB types regenerated and committed?

Flag any migration not yet applied to the deploy target. Confirm explicitly before deploying code that depends on an unapplied migration.

## Env var changes

- New env vars referenced in code not in `.env.example`.
- Env vars used as `process.env.X!` — runtime crash if absent. Verify presence in the deploy target.
- Provider keys that may have rotated.

## Provider / capacity changes

- Rate-limit configuration changed? New effective cap per user per day?
- Error-sink config changed? A new error path that fires per-request can exhaust quota in minutes.
- AI prompt or model changed? Apply **VERSION-GUARD** (`~/.claude/REVIEWER_CONVENTIONS.md` §6) — output-shape change requires the DB version column bumped, not just the code constant. (For the prompt-safety surface itself, run `/ai-prompt-review`.)
- New sub-processor added? Privacy policy needs an update.

## Behavioural surface

For each non-trivial change since last deploy:

- Rollback plan: revert cleanly, or does it depend on a non-revertible migration?
- User-visible behaviour change on the first request after deploy.
- Cached/derived rows from the old shape rendering incorrectly under new code? Symmetric `generator_version` guards on reader and writer prevent this; verify they exist.

## Ship-surface hygiene

- `console.log` / `console.error` / `debugger` introduced.
- Test-only API endpoints exposed in production builds (any `/dev/*` route gated on `NODE_ENV !== "production"`).
- Hard-coded test data, dummy emails, fake user ids.
- Broken internal links: every `href` / `<Link>` / `router.push` / `redirect` target touched since the base resolves to a real route on disk (App Router: drop `(group)` segments, match `[param]` dynamics). A link to a deleted/unbuilt page is a live 404 inside the app — resolve each, don't eyeball.
- Gate responses preserve input: any submit handler reachable in this deploy that can return 403 / paywall keeps the user's filled form and inlines the upgrade, rather than hard-redirecting and discarding a multi-step entry.

## Output (delta mode)

Severity-ranked, scoped to this deploy:

- `BLOCKER` — must fix before deploy (verification failure, unapplied migration, env var missing, secret in diff)
- `RISK` — could fix or could go with a watch (large surface change, new sub-processor, new error path with per-request capture)
- `WATCH` — note for post-deploy monitoring

End with:

- `READY TO DEPLOY` — no BLOCKERs
- `NOT READY` — list BLOCKERs
- Suggested post-deploy watch list (what to monitor for the first 30 minutes after rollout)

---

# `scope=full` — launch readiness

The job: audit the whole app for launch readiness across security, privacy, UX, and infrastructure. Run at major milestones (first public users, paid launch, regulatory cohort).

## Discover the stack

Identify before checking categories:

- Web framework, server runtime, hosting target
- DB and its auth/authz model
- Auth provider (managed service vs hand-rolled)
- AI / external API providers in use
- Error sink and feature-flag system
- Email/SMS sender and its rate limits

Don't grep for `bcrypt` if the project uses managed auth; don't assume `index.html` if it's server-rendered.

## Security, privacy, mobile, a11y, perf, observability, deps — delegate, don't re-audit

Run the dedicated audits and fold their findings into this report by severity:

- Access / auth / rate-limit / origin / user-id filtering / RLS → `/check-access`
- PII flows, deletion cascade, export, sub-processor list, error-sink scrubbing → `/privacy-audit`
- Touch targets, contrast, input font-size, soft-keyboard, PWA manifest → `/mobile-check` (user-facing pages)
- Screen-reader / keyboard / semantics / WCAG AA → `/a11y-check` (user-facing pages)
- N+1, unbounded reads, missing indexes, bundle weight → `/perf-check`
- Critical-path instrumentation, error-sink capture/latching, alerts on money/auth → `/observability-check`
- Dependency vulns, lockfile integrity, license, unmaintained deps → `/dep-audit`

Then add only the launch-specific checks those don't cover:

### Security (launch-only residue)

- Secrets server-side only — grep the client bundle for `sk_`, `xoxb_`, `AKIA`, etc.
- Source maps in the deploy build don't expose server code without auth.
- Open-redirect validation on any `next`/`redirect`/`return_to` query: starts with `/`, not `//`, no backslashes, no ASCII control chars.

### Legal / compliance

- Privacy policy + terms of service linked from auth and footer.
- Account-deletion endpoint exists, cascades through every user-scoped table (verify FK cascades), reachable from settings.
- Data-export endpoint if the policy promises portability.
- Cookie consent if anything beyond essential session cookies is set.
- For EU/UK/CA users: DSR flow described in policy.

### UX (launch-only, non-mobile)

- Loading + saving states; no silently-disabled buttons; every error path offers a next action.
- Gated submits preserve input — apply **GATE-PRESERVE** (`~/.claude/REVIEWER_CONVENTIONS.md` §6): a 403/paywall keeps the filled form and inlines the upgrade, never a hard redirect that discards a multi-step entry.
- Onboarding flow runs end-to-end as a brand-new user on a phone-sized viewport.
- Every nav link resolves to a real page — apply **LINK-RESOLVE** (§6) across the repo's nav targets; a dangling target is a live 404.

## Subscription / payment lifecycle

If the app charges money, the payment path is the highest-risk surface — audit it explicitly, not just as "an endpoint."

- **Money is never granted by a user-callable endpoint.** Entitlement (`status = active`) is written only by a verified provider webhook, never by a route the client can POST directly. A mock/`createSubscription`-style direct activation must be gone before real charges.
- **Audit the checkout-session CREATION, not just the webhook.** If the webhook/fulfillment logic assumes a payment-method class (card-only, synchronous settlement) and filters others (e.g. ignores `async_payment_succeeded`), the session-creation call MUST pin the method in code (`payment_method_types: ["card"]` or equivalent). Omitting it hands method selection to the provider's dashboard — a driftable toggle guarding money: enable an async bank method later and sessions complete UNPAID and never fulfill. Verify the amount/entitlement is re-derived server-side from a code table, never an echoed client value.
- **Webhook signature verification** on every payment webhook, with the raw (unparsed) body — most SDKs require the raw bytes to verify. Reject unsigned/invalid.
- **Idempotent entitlement writes.** Providers retry webhooks; the same event delivered twice must not double-grant, double-charge-credit, or flip state twice. Dedup on the provider's event id.
- **No half-upgraded state.** A failed/abandoned checkout leaves the user exactly as before — no `active` row written on a payment that didn't clear.
- **Downgrade paths exist and are correct:** cancellation, failed renewal (dunning), refund/chargeback all move the user back to the un-entitled state. Cancelled→active requires a _new_ checkout, not a re-POST.
- **Free-window / trial anchor** can't be reset by the user to farm another free period (the anchor column is server-write-only).
- **Kill switch:** can you halt new subscriptions without a redeploy?

## Operational kill switches

- Subscription/payment: can you halt new sign-ups?
- AI endpoints: can you disable each individually?
- Webhook intake: can you drop on the floor?

Pre-launch projects rarely have these and find out at 2am.

## Infrastructure

- All env vars in `.env.example`. Production has them all set.
- Fresh-clone build succeeds clean.
- DB migrations all applied to deploy target — flag any unpushed.
- Production-grade email sender configured (not the auth provider's default-capped relay).
- Error sink quota and alerting configured. Per-error-kind cooldown latching in code paths that can fail per-request.
- **CI fast-signal gate:** if the project commits to main with auto-deploy and has no push-triggered typecheck/lint/build check, recommend `/ci-check` — moving that signal ahead of the deploy build (and adding lint the build may skip) is low-effort. Note it's a recommendation, not a BLOCKER: the deploy provider already fails on a broken build. Template-derived apps ship with a green suite and gate tests from day one; only legacy repos without a suite defer test-gating.

## Output (full mode)

Severity-ranked:

- `CRITICAL` — ship blocker (privacy leak, paywall bypass, unauthenticated access)
- `IMPORTANT` — should fix before launch
- `NICE-TO-HAVE` — track, don't block

For each finding: category, file/area, one-line "what could go wrong", suggested next action.

End with:

- Counts by severity.
- Single highest-leverage fix.
- Longest-lead-time fix (so the user starts it now).

---

# Post-deploy smoke (run AFTER rollout, both modes)

The audit above runs _before_ you ship. This runs _after_ — a pre-deploy pass that's green tells you nothing about whether prod is actually serving. Do not declare a deploy successful until these pass against the live target.

Propose the smoke list (don't blindly hit prod — confirm the target and that it's safe):

- **Liveness:** the app's health/root route returns 200 (not a 500 page, not a stale cached build).
- **One authed read:** a logged-in user can load a core page that does a real DB read — proves auth + DB + RLS survived the deploy.
- **One critical write path** (use a test account, not a real user): the primary action completes end-to-end. For a paid app, the checkout→entitlement path is the one to verify.
- **New surface from this deploy:** exercise whatever changed — the new endpoint/page actually responds, not just compiles.
- **Migrations:** if a migration shipped, confirm it's applied on the target (a code-depends-on-unapplied-migration deploy fails only at request time).
- **Error sink:** confirm events are arriving and not flooding (a new per-request capture path shows up here within minutes).

Report each as PASS / FAIL / SKIPPED (reason). A FAIL here means **roll back**, not "investigate later" — the users are already hitting it.

---

# Both modes — always end with

- Scope used (`delta since <sha>` or `full repo`).
- Target (`staging` or `prod`) — risk tolerance differs.
- Total findings by severity.
- Exceptions applied count + any suppressed BLOCKER/CRITICAL listed.
- Final verdict.

$ARGUMENTS
