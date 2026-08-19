---
name: add-page
description: Scaffold a new UI page — route-group placement, mobile-first defaults, multi-step/wizard traps, error/empty states, nav entry. Use for adding ONE frontend page. For the backend it talks to use /add-endpoint; for a whole feature use /add-feature.
---

Scaffold a new page. Description: $ARGUMENTS

## Discover first

Apply **DISCOVER-FIRST** (`~/.claude/REVIEWER_CONVENTIONS.md` §6), then narrow to this layer: the framework + router, the project's server-vs-client-component default, its data-fetching convention (server actions / `loader` / hooks), the styling system, and shared layout primitives (top bar, bottom tab bar, auth gate). **Read one nearby sibling page end-to-end — that's your template.**

## Pick the location

- **Authenticated user page** → the project's authenticated route group / layout. Don't duplicate auth at the page.
- **Auth page** → the auth route group.
- **Public / unauthenticated** → root or `(public)`.
- **Admin** → admin group with the admin-check helper, not the paid gate.

## Compose

Match the existing pattern: server vs client component default, data-fetching convention, state library if any.

## Mobile-first defaults (non-negotiable)

Apply **MOBILE-FLOOR** (`~/.claude/REVIEWER_CONVENTIONS.md` §6): input font-size ≥ 16px, tap targets ≥ 44pt/48dp, contrast ≥ 4.5:1 body and ≥ 3:1 large, ≥ 16px horizontal padding, and bottom space reserved for any fixed tab bar. The numbers are maintained there and audited by `/mobile-check` — don't restate them here.

If the project's existing pages violate the floor, match the floor, not the siblings. For a deeper pass run `/mobile-check` on the new page.

## Multi-step / wizard pages

- **Key sensor-holding components by current step.** `<VoiceInput key={currentStep.key} />`. React reuses instances at the same tree position otherwise; async transcripts fire against the wrong field.
- **`setState` then `submit` in the same tick reads stale state.** For select-buttons that update state and submit, pass the value into the submit handler explicitly.
- **Strict-mode double-invocation** — for effects that do server writes, guard with `useRef`: `if (started.current) return; started.current = true;`. Server-side dedup is the other half.
- **Progressive save** — save after each completed step, not at the end.

## Errors and empty states

- Every error path offers a next action. Never a dead-end "Done" after partial failure.
- Empty states have specific copy, not "no data".
- Loading states finish — no indefinite spinners on failed fetch.
- **Gated submits preserve input** — apply **GATE-PRESERVE** (`~/.claude/REVIEWER_CONVENTIONS.md` §6): if a submit can return 403 / paywall / auth-required, keep the filled form mounted, snapshot any prior output, and inline the upgrade — never `router.push(...)` away from a filled multi-step form. If the project already has an inline-gate pattern on a sibling flow, copy it.

## Nav entry

If the page needs a nav entry, add it — and apply **LINK-RESOLVE** (§6): resolve the target against the route tree on disk; don't assume it exists. A broken nav link inside an authenticated app destroys trust faster than a missing feature.

## Verify

Type check + lint. Mentally render at 375px before declaring done. Resolve every internal link target the page introduces against a real route (**LINK-RESOLVE**).
