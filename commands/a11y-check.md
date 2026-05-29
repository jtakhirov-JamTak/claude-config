---
name: a11y-check
description: Audit accessibility against WCAG 2.2 AA — semantics, ARIA, keyboard operability, focus order, labels, status announcements, contrast for assistive-tech users. ("Keyboard" = physical/AT navigation.) Use for a screen-reader / keyboard / semantics pass on UI. NOT mobile-device issues incl. soft-keyboard occlusion, tap targets, viewport, PWA-install (use /mobile-check); NOT general code review (use /review-changes).
---

Audit accessibility against WCAG 2.2 AA. Output is a severity-ranked report keyed to success criteria, not a fix. Scope: $ARGUMENTS

## Reviewer conventions (apply to this skill)

- **Scope**: `$ARGUMENTS` may name a page / component / dir / glob; default scope is the pages touched by uncommitted changes.
- **Exceptions**: read `.claude/exceptions.md` at repo root before reporting; skip matching entries; surface any suppressed must-fix at the end.
- **Caps**: honor `top=N`, `critical-only` (blocks-AT-users only), `high-only`, `unbounded`. Default: at most 5 minor findings listed individually, rest summarized.
- **Long-form rules**: `~/.claude/REVIEWER_CONVENTIONS.md`.

## Discover first

Confirm the framework and component library (a UI kit may handle focus/ARIA for you — or may not). Note whether the app is mobile-first PWA: same DOM serves AT users on desktop and mobile, so a keyboard/SR gap ships to everyone. The boundary with `/mobile-check`: that skill owns the *device* (touch, viewport, soft-keyboard occlusion, install); this skill owns *assistive technology* (screen reader, physical keyboard, semantics). Contrast is shared — report it here in WCAG terms, there in mobile-legibility terms.

## Perceivable

- **Text alternatives** (1.1.1): every `<img>`/icon/media has alt text, or `alt=""` + `aria-hidden` if decorative. Icon-only buttons have an accessible name.
- **Info & relationships** (1.3.1): structure is semantic — `<button>` not `<div onClick>`, `<nav>/<main>/<header>`, real lists, `<label>`-bound inputs. Heading levels don't skip (h1→h3).
- **Contrast** (1.4.3): text ≥ 4.5:1, large text / UI components & focus indicators ≥ 3:1. Cite the failing pair.
- **Reflow / text spacing** (1.4.10/1.4.12): content survives 200% zoom and increased spacing without clipping.

## Operable

- **Keyboard** (2.1.1/2.1.2): every interactive element reachable and operable by keyboard; no focus traps; custom widgets (menus, dialogs, comboboxes) implement the expected key handling.
- **Focus order & visible focus** (2.4.3/2.4.7): tab order follows reading order; focus is always visible (no `outline: none` without a replacement); on dialog open, focus moves in and is restored on close.
- **Target size** (2.5.8, AA): pointer targets ≥ 24×24 CSS px (the WCAG AA floor — note this is *below* the 44/48 mobile guideline `/mobile-check` enforces; cite both bars where relevant, don't duplicate the finding).
- **Bypass blocks** (2.4.1): a skip-link or landmark structure to bypass repeated nav.

## Understandable

- **Labels & instructions** (3.3.2): inputs have persistent visible labels (placeholder is not a label).
- **Error identification & suggestion** (3.3.1/3.3.3): errors are announced to AT (`aria-live` / `role="alert"` / `aria-invalid` + described-by), not colour-only, and say how to fix.
- **On-focus / on-input** (3.2.1/3.2.2): focusing or changing a field doesn't trigger a surprise context change.

## Robust

- **Name/role/value** (4.1.2): custom controls expose correct role + state (`aria-expanded`, `aria-checked`, `aria-selected`).
- **Status messages** (4.1.3): async results (saved, error, count updated) reach an `aria-live` region.

## Output

For each issue: `file / component — WCAG SC — what an AT user experiences — what to change — priority`.

Priority:
- `must fix` — blocks an AT user from completing a task (no keyboard path, unlabelled critical control, trap).
- `should fix` — degrades but doesn't block (poor focus order, missing live-region on a non-critical status).
- `minor` — polish.

End with: counts by priority, scope, the single highest-leverage fix, and a verdict — `WCAG AA: conformant on this surface` / `gaps (n must-fix)` / `not conformant`.

$ARGUMENTS
