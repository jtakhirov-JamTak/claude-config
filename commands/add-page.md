---
name: add-page
description: Scaffold a new UI page — route-group placement, mobile-first defaults, multi-step/wizard traps, error/empty states, nav entry. Use for adding ONE frontend page. For the backend it talks to use /add-endpoint; for a whole feature use /add-feature.
---

Scaffold a new page. Description: $ARGUMENTS

## Discover first

Read `package.json`, confirm the framework + router, and **read one nearby sibling page end-to-end — that's your template.** Note the project's server-vs-client-component default, data-fetching convention (server actions / `loader` / hooks), styling system, and shared layout primitives (top bar, bottom tab bar, auth gate).

## Pick the location

- **Authenticated user page** → the project's authenticated route group / layout. Don't duplicate auth at the page.
- **Auth page** → the auth route group.
- **Public / unauthenticated** → root or `(public)`.
- **Admin** → admin group with the admin-check helper, not the paid gate.

## Compose

Match the existing pattern: server vs client component default, data-fetching convention, state library if any.

## Mobile-first defaults (non-negotiable)

- **Input font-size ≥ 16px** (iOS zooms on focus below 16px).
- **Tap targets ≥ 44pt iOS / 48dp Android.** Wrap native checkboxes in `<label>` with `min-h-11`.
- **Reserve space for fixed bottom bars** — hub/list pages need bottom padding so the last card isn't covered.
- **Contrast meets WCAG AA** — ≥ 4.5:1 body, ≥ 3:1 large/decorative. Default mid-grey utilities (`text-zinc-400`, `text-gray-400`) fail AA at small sizes.
- **Horizontal padding ≥ 16px** from viewport edges.

If the project's existing pages violate these, match the rules, not the siblings. For a deeper pass run `/mobile-check` on the new page.

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
