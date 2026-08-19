---
name: mobile-check
description: Audit mobile-DEVICE UX — touch targets, contrast, inputs, soft-keyboard occlusion, scroll, viewport, PWA manifest/install. Use for a mobile-device pass on UI. NOT assistive-tech a11y — keyboard nav, screen readers, semantics (use /a11y-check); NOT general code review (use /review-changes); NOT break-it scenarios (use /grill).
---

Audit one or more pages for mobile-first UX issues.

## Reviewer conventions (apply to this skill)

- **Scope**: `$ARGUMENTS` may name a page, component, dir, or glob; default scope is the pages touched by uncommitted changes.
- **Exceptions**: read `.claude/exceptions.md` at repo root before reporting; skip matching entries; surface any suppressed must-fix at the end.
- **Caps**: honor `top=N`, `critical-only` (must-fix only), `high-only` (must-fix + should-fix), `unbounded` in `$ARGUMENTS`. Default: at most 5 nice-to-have findings listed individually, rest summarized.
- **Long-form rules**: `~/.claude/REVIEWER_CONVENTIONS.md`.

## Discovery first

- Confirm the framework (React/Svelte/Vue/etc.) and the styling system (Tailwind, CSS Modules, styled-components, vanilla CSS). Class names and audit techniques differ.
- Note any project-wide layout primitives (top bar, bottom tab bar, safe-area handling). If a bottom tab bar exists, every hub/list/scroll page must reserve space for it.

## The floor, then the rest

Start from **MOBILE-FLOOR** (`~/.claude/REVIEWER_CONVENTIONS.md` §6) — input font-size ≥ 16px, tap targets ≥ 44pt/48dp (checkbox rows wrapped in a `<label>` with `min-h-11`), contrast ≥ 4.5:1 body and ≥ 3:1 large, ≥ 16px horizontal padding, bottom space reserved for a fixed tab bar. Those five are the baseline this skill enforces; **when a number changes, change it in §6**, not here. Everything below is the device audit the floor doesn't cover.

## Layout

- Nothing scrolls horizontally at a 375px viewport. Common culprits: fixed widths, oversized `min-width`, `whitespace-nowrap` on long strings, tables.
- Content stacks at narrow widths; no two-column layout below ~640px without a fallback.

## Touch targets — beyond the floor

- Subtle text links (`text-xs underline`, footer "edit"/"reset" links) need an inflated tap target via padding even when the visual size stays small.
- ≥ 8px gap between adjacent tappable elements so a thumb doesn't hit both.

## Typography — beyond the floor

- Headings sized for narrow screens — a 48px heading wraps awkwardly at 375px.
- Cite the failing colour pair when contrast fails; the mid-grey utilities (`text-zinc-400`, `text-gray-400`, `#9CA3AF`-ish) are the usual offenders.

## Inputs and keyboard

"Keyboard" here means the **on-screen/soft keyboard** — its layout and whether it occludes inputs. Physical-keyboard operability, focus order, and screen-reader behaviour are `/a11y-check`'s job, not this skill's.

- Inputs use a correct `type` / `inputmode`: `email`, `tel`, `numeric`, `decimal`, `search`. Wrong inputmode gives users a useless keyboard.
- Textareas are tall enough to start using without growing — at least 3 lines visible.
- When an input near the bottom of the page is focused, the mobile keyboard doesn't cover it. Test: focus the last form field, verify it scrolls into view. `scrollIntoView({ block: "nearest" })` on focus, or a bottom spacer, fixes this.
- Dropdowns and pickers that open above the keyboard need explicit scroll-into-view on open.

## Interaction model (mobile-only traps)

- Outside-click dismiss handlers use `pointerdown` (covers both mouse and touch). `mousedown` misfires on iOS Safari and leaves popovers stuck open.
- Multi-step forms key any sensor- or media-holding component (mic, camera, picker) by the current step. Otherwise React reuses the instance at the same tree position and an async transcript can fire against the wrong field.
- Double-tap-to-submit is guarded with a `useRef` `inFlight` flag, not just a `disabled` prop — `disabled` is the UX, the ref is the guarantee.

## Performance feel

- Skeleton placeholders for content above the fold, not just spinners. A spinner says "wait"; a skeleton says "almost there".
- Images use the framework's image primitive (Next/Image, Astro/Image, etc.) or have explicit width/height to prevent layout shift.
- Lists don't block the page while loading — render the chrome immediately, fill in the list.

## PWA / standalone

- If the app is installable, the manifest has `name`, `short_name`, `start_url`, `display: standalone`, `theme_color`, `background_color`, and at minimum 192px and 512px icons.
- Theme colour matches the actual top-bar colour. Mismatched theme colour makes the standalone install look broken.
- No browser chrome leaks in standalone mode (no visible address bar, no body scroll-bounce showing a different colour underneath).

## Output

For each issue: `file (or component) — what's wrong in plain English — what to change — priority`.

Priority:

- `must fix` — silently breaks input, blocks tap, fails contrast
- `should fix` — degrades feel
- `nice to have` — polish

End with a one-line verdict: `mobile-ready` / `needs work (n must-fix)` / `not mobile-ready`.

$ARGUMENTS
