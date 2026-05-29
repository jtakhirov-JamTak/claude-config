# Skills Maintenance Protocol

The one page that governs the `~/.claude/commands/` + `~/.claude/agents/` skill set.
Not always-loaded — read it when adding, renaming, retiring, or adopting skills.

## 1. Layers — where things live

- **Agnostic core** = the skill bodies in `~/.claude/commands/` (+ agents in `~/.claude/agents/`). User-global, so every project gets them automatically. Each skill is stack-neutral and opens with a **"Discover first"** step that reads the repo and matches the nearest sibling.
- **Opinionated layer** is NOT separate files. It's two things:
  1. `~/.claude/REVIEWER_CONVENTIONS.md` — shared review conventions (§1–§4) + canonical checks cited by ID (§6: LINK-RESOLVE, GATE-PRESERVE, DB-ERROR-CHECK, VERSION-GUARD). **Improve a check HERE once; every citing skill inherits it.**
  2. Each repo's `CLAUDE.md` (stack, house rules) + `.claude/exceptions.md` (accepted findings). The skill adapts to the repo via Discover-first; the repo declares its specifics here.

Rationale for not splitting core/opinion into paired files: it would double the file count and re-introduce triggering ambiguity. Spine + discover-block in one file is the pattern.

## 2. Naming convention

- **Scaffolders:** `add-<layer>` (`add-endpoint`, `add-table`…) + the `add` router.
- **Audits / reviewers (going forward):** `<domain>-check` — `mobile-check`, `perf-check`, `a11y-check`, `db-check`, `ci-check`, `observability-check`.
- **Actions / workflow:** `<verb>` or `<verb>-<noun>` — `commit`, `fix-bug`, `save-context`, `worktree`, `test`.
- **Grandfathered (do NOT mass-rename):** `check-access` (verb-first), `privacy-audit` / `dep-audit` (`-audit`), `ai-prompt-review` / `review-changes` (`-review`). They're referenced by orchestrators, `REVIEWER_CONVENTIONS.md`, and memory; the cosmetic gain of renaming is below the breakage risk (same call as the deferred `verify-app` rename). New audits use `<domain>-check`.

## 3. File structure (canonical SKILL.md)

```
---
name: <kebab>
description: <one-line what> — <when to use>. NOT <x> (use /y); NOT <z> (use /w).
---
<one-line purpose> + $ARGUMENTS
## Reviewer conventions (reviewers only)   ← compact 4-line block + pointer to REVIEWER_CONVENTIONS.md
## Discover first
## <Steps | Checks>
## Output                                   ← severity ladder + one-line verdict
$ARGUMENTS
```

**Description rule (keeps always-loaded lean):** one line of *what* + *when* + the NOT-clauses. No check-list enumerations in the description — those live in the body. The NOT-clauses are load-bearing (they're the triggering disambiguation); never drop one to save tokens.

## 4. Adopting the set in a new project

Skills are user-global, so there is no per-project install. Four steps:
1. Nothing to copy — `/…` commands already resolve in the new repo.
2. Add a repo `CLAUDE.md` (or run `/init`) describing the stack + house rules.
3. Copy the `.claude/exceptions.md` template into the new repo root.
4. First run of any reviewer auto-discovers the stack. If the stack differs (e.g. Express/Drizzle vs Next/Supabase), Discover-first handles it — no skill edits.

## 5. Versioning & retirement

- Skills are prompts, not data — no version stamps. The single source for shared checks is `REVIEWER_CONVENTIONS.md §6`; edit it once, all citers inherit.
- **Add an item:** name per §2; if it's a reviewer, add it to the `REVIEWER_CONVENTIONS.md` roster and wire it into `full-review` / `deploy-check` if it belongs in a pipeline; write a VERIFY block (3 should-fire / 3 should-NOT) and route-test against the live set before trusting it.
- **Retire an item:** delete the file, then grep for dangling references — `full-review`, `deploy-check`, the `REVIEWER_CONVENTIONS.md` roster, and `/x` cross-refs in other descriptions. (LINK-RESOLVE applied to the skill set itself.)
- **Merge rule:** never merge two items if it blurs a distinct trigger or drops a capability. Efficiency comes from trimming descriptions and sharing rules by reference — never from collapsing capabilities.

## 6. Orchestrator wiring (current)

- `full-review` → verify-app, simplify, grill, review-changes, (cond.) security-review, ai-prompt-review, staff-reviewer, perf-check, mobile-check, a11y-check, privacy-audit.
- `deploy-check scope=full` → delegates to check-access, privacy-audit, mobile-check, a11y-check, perf-check, observability-check, dep-audit; recommends ci-check.
- `fix-bug` §5 → recommends `/test write` to lock the regression.

Keep this section current when wiring changes — it's the map a retirement grep checks against.
