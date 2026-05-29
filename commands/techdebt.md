---
name: techdebt
description: Scan for dead code, dead UI, duplication, and cleanup opportunities — then fix approved items. Use for a repo-wide dead-code/dead-UI/duplication sweep with an approve-before-fix gate. NOT a quality pass on the current diff (use the built-in /simplify), NOT a correctness review (use /review-changes).
---

Two-phase: scan and propose, then fix only what the user approves. The highest-yield category is usually *dead code left over from a removed feature* — type-clean deletion routinely leaves stale UI copy, dead nav entries, dead prompts, and orphan helpers behind. Sweep that aggressively.

## Reviewer conventions (apply to this skill)

- **Scope**: `$ARGUMENTS` may name a dir or glob to narrow the scan; default scope is the whole repo.
- **Exceptions**: read `.claude/exceptions.md` at repo root before reporting; skip matching entries. Common techdebt exceptions: dynamically-imported routes that look unreferenced, intentionally-kept TODO markers tied to a tracked ticket.
- **Caps**: honor `top=N`, `critical-only` (quick wins only), `high-only` (quick wins + medium effort), `unbounded` in `$ARGUMENTS`. Default: list every quick-win individually; cap medium-effort at 10; summarize the rest by category.
- **Long-form rules**: `~/.claude/REVIEWER_CONVENTIONS.md`.

## Phase 1 — Scan

Run each of these passes and collect findings into a single grouped list.

### 1. Dead code (the easy half)
- Unreferenced exports — symbols exported but never imported.
- Unreferenced files — module not imported from anywhere, not a route entry, not in a manifest.
- Unused imports inside live files.
- Unreachable branches (dead `if (false)`, conditions on always-true constants, post-`return` code).
- Components defined but never rendered.

### 2. Dead UI and copy (the half people miss)
After any feature removal, deletion that passes type-check still typically leaves:
- **Dead nav links** — entries in top bars, side menus, footer menus, bottom tabs that point to a removed page (404 on click).
- **Dead UI tiles** — hub-page cards / feature grids that still surface a removed module.
- **Stale prompt copy** — AI system prompts that still reference a feature the model can no longer produce.
- **Stale empty-state copy** — "Click X to start" where X is gone.
- **Stale settings / preferences** — toggles for a feature that no longer exists.
- **Stale help / about / docs strings** that name removed features.

Grep for the name of any removed-but-might-still-be-referenced feature/module/concept across the entire repo. Don't trust the type checker — copy isn't typed.

### 3. Duplication
- Same constant / enum defined in two places.
- Same logic in two helpers under different names.
- Same network call wrapper / fetch shape repeated across files instead of one client.
- Same validation rule expressed twice (server schema and a separate client check that drifted).

### 4. Drift from a central helper
- Inlined access checks where a centralized gating helper exists.
- Hand-rolled error capture where a central wrapper exists.
- Hand-rolled fetch where a project client exists.

### 5. Structure
- Files over 500 lines that mix unrelated concerns and could split.
- Components doing both data fetching and presentation that the project elsewhere separates.
- Mixed patterns where the codebase has clearly converged (e.g. form library X used in 12 places, hand-rolled `useState` form in this one).

### 6. Markers
- TODO / FIXME / HACK / XXX comments — list them with date if traceable.
- Commented-out blocks of code (delete, don't preserve).

### 7. Deps and assets
- Unused dependencies in `package.json` (imported nowhere).
- Stale lockfile entries.
- Stale fixtures / temp files / archives in the repo.

## Phase 2 — Group and propose

Present findings grouped by safety:

- **Quick wins (safe)** — unused imports, dead files no one imports, dead nav links pointing to removed pages, commented-out code.
- **Medium effort (small refactor)** — duplicated constants, drift from a central helper, mixed patterns.
- **Bigger items (plan first)** — split a large file, replace one form lib with another, restructure a directory.

For each finding: one-line description, file path(s), and a one-line "why it matters" if non-obvious.

Ask which groups to fix. Do not touch anything until approved.

## Phase 3 — Fix approved items

For each approved group:
1. Make the changes.
2. Run type check + lint + unit tests.
3. If anything breaks, undo immediately and report what happened — do not chase fixes through a rabbit hole.
4. After all groups for this session: run a fresh `grep` for the removed names to confirm no straggling references.

## Output

- Total findings by category.
- Total fixed this session.
- Skipped items with one-line rationale.
- Remaining tracked-for-later list.

$ARGUMENTS
