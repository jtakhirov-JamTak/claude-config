---
name: check-access
description: Audit API routes and gated pages for missing/inconsistent access enforcement — auth, user-id filtering, origin, rate-limit, RLS, gate-helper drift. Use to sweep the access surface or scope to a route/dir. NOT a general security pass (use the built-in /security-review); NOT a diff review (use /review-changes); NOT the privacy slice (use /privacy-audit).
---

Audit the project for missing or drifting access enforcement. The output is a severity-ranked report, not a fix.

## Reviewer conventions (apply to this skill)

- **Scope**: `$ARGUMENTS` may name a file / dir / glob / symbol; default scope is all API routes.
- **Exceptions**: read `.claude/exceptions.md` at repo root before reporting; skip matching entries; surface any suppressed CRITICAL at the end.
- **Caps**: honor `top=N`, `critical-only`, `high-only`, `unbounded` in `$ARGUMENTS`. Default: at most 5 LOW + 10 MEDIUM listed individually, rest summarized.
- **Long-form rules**: `~/.claude/REVIEWER_CONVENTIONS.md`.

## Step 0 — Discover the project's gating helpers

Before grepping for missing checks, find what "present" looks like in this codebase:

1. Locate the central gating helpers (names vary):
   - Paid-only / subscription gate
   - Tiered or free-window gates (some projects have one, others have two or three)
   - Admin bypass / admin-only gate
   - Auth helper
   - Origin / CSRF helper
   - Rate-limit helper
   - Request-body schema parser
2. Note the exact symbol name of each — you'll grep for these, not for generic words like `auth`.
3. If there's no central paid/access helper and you find the gate logic inlined across multiple routes, that itself is finding `CRITICAL #1`. Stop the per-route audit and surface the drift first.

## Step 1 — Enumerate routes and gated pages

- Find all API route files (`app/api/**`, `pages/api/**`, `routes/**`, etc.).
- Find all server-rendered pages whose data should be paid-only or tier-restricted.

## Step 2 — Per route, verify the pipeline

For each **mutating** route (`POST` / `PATCH` / `PUT` / `DELETE`):

1. Origin / CSRF check present
2. Auth helper called
3. Rate limit applied — and both a per-minute AND a per-day cap (a per-minute cap alone does not bound daily exfiltration)
4. Request body parsed against a schema
5. Access gate matched to the route's tier
6. All DB queries filter by the _authenticated_ principal id, not a client-provided id

For each **enumeration** GET that lists user-scoped data, apply **READ-SURFACE-LIMITS** (`~/.claude/REVIEWER_CONVENTIONS.md` §6):

1. Auth helper called
2. Per-day read cap applied (unbounded enumeration GETs are the leak path a compromised session will use)
3. Explicit `.limit()` on every query — and check whether it exceeds the client's own row ceiling, which truncates silently rather than erroring
4. All queries filter by the authenticated principal id
5. Do **not** flag a missing origin/CSRF check here — it is not the control that guards reads, and it 403s same-origin downloads where `Origin` is absent. Audit the cookie `SameSite` attribute and the CORS allow-list instead; those are what actually bound cross-site reads.

For each **server-rendered gated page**: the access gate is called exactly once, and that call lives in the page or its layout — not duplicated across both.

## Step 3 — Per route, verify the exclusions

Apply **GATE-EXCLUSIONS** (`~/.claude/REVIEWER_CONVENTIONS.md` §6) — the five routes that must never carry the paywall/access gate (auth callback, subscription-creating endpoint, pre-payment onboarding writes, webhook receivers, admin routes).

Flag any route that _is_ gated but shouldn't be — those break first-touch flows for new users.

## Step 4 — Cross-cutting checks

- Inlined gate logic anywhere (raw `if (!hasAccess) return 403` blocks scattered across routes instead of a single helper call) — every instance is a `HIGH` finding.
- Two variants of the gate helper used for the same tier — drift waiting to happen.
- Routes with auth but no rate limit, or rate limit but no per-day cap.
- Mutating routes missing the origin/CSRF check. (Its *absence on a read GET* is not a finding — see **READ-SURFACE-LIMITS**.)
- A post-auth redirect parameter (`next`, `returnTo`, `redirectTo`) used without validation — apply **REDIRECT-VALIDATE** (`~/.claude/REVIEWER_CONVENTIONS.md` §6). Reject anything not starting `/`, anything starting `//`, and any backslash or control character.
- Cookie `SameSite` set to `None`, or a CORS allow-list that reflects arbitrary origins with credentials — the two settings that actually expose the read surface.
- Pages where the gate is duplicated in both the layout and the page (double-source-of-truth).

## Step 5 — Report

Severity-ranked. For each finding:

- Severity: `CRITICAL` (unauth access possible / paywall bypass), `HIGH` (drift between policy and implementation), `MEDIUM` (missing defense-in-depth like per-day limit), `LOW` (style or naming inconsistency).
- File and approximate line.
- The specific helper that's missing (named by the symbol you discovered in Step 0).
- A one-line "what would go wrong" — not a fix.

End the report with: total routes audited, total gaps by severity, and one recommendation for which finding to fix first.

## What "good" looks like

A single helper, grep-able by name, called identically at the top of every gated route. If you can answer "which routes are paid-only?" with one grep, the architecture is right. If you have to read each route to find out, that's the drift this audit exists to surface.

$ARGUMENTS
