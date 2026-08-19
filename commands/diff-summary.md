---
name: diff-summary
description: Plain non-technical English summary of what changed — committed, staged, and unsaved — with anything risky called out in the same simple language. Use when you want to know WHAT HAPPENED without reading code. NOT a severity-ranked correctness review (use /review-changes); NOT the pre-deploy gate (use /deploy-check); NOT an explanation of how existing code works (use /explain).
---

Summarize recent work in plain English. `$ARGUMENTS` may name a commit count (`10`), a path to scope to, or a branch to compare against; default is the last 5 commits plus everything not yet committed.

## Gather

```
git log --oneline -<n>            # recent commits (default 5)
git status --short                # staged vs unsaved vs untracked
git diff --stat                   # unsaved, by file
git diff --cached --stat          # staged, by file
```

Read the actual diff for anything you are about to describe. **Never summarize a change from its filename or commit message** — commit messages are frequently wrong about what the commit did, and that is exactly the drift this command exists to catch.

If there are no commits, a detached HEAD, or nothing changed, say so in one line and stop. Do not invent activity.

## Say it plainly

- Describe the **effect on the person using the app**, not the mechanism. "The save button now works on phones" — not "fixed the touch handler in `EntryForm.tsx`".
- No file names, no function names, no jargon in the main summary.
- Group aggressively. Twenty small edits to one page become "several small fixes to the journal page." Detail is available on request; a wall of bullets is not a summary.
- Separate **saved** (committed), **staged**, and **not saved yet** — the user's real question is usually "what would I lose right now?"

## Call out risk — this is the part that matters

A friendly summary that hides a dangerous change is worse than no summary. Scan the diff for these and surface them in the same simple language, at the top, before the normal summary:

- **Data loss** — a `DROP`, a `DELETE`, a migration without a backfill, a hard delete where the project's rule is archive.
- **Secrets** — anything that looks like a key, token, or password in tracked files.
- **Money or access** — changes to payment, subscription, entitlement, or auth checks.
- **A weakened check** — a test deleted, a gate loosened, a threshold raised, `--no-verify`, a skipped assertion.

Apply **PATTERN-REPEATS** (`~/.claude/REVIEWER_CONVENTIONS.md` §6): if one instance shows up, grep for the rest before reporting the count.

Say what it means, not what it is: "This change permanently deletes habit records instead of hiding them — if that runs, the data is gone" beats "hard delete in `habits.ts`."

This is a *flag*, not a review. Name it, say why it matters, and point at `/review-changes` for the full pass.

## Output

```
⚠️  Worth looking at first
- <plain-language risk, and what it would cost>

Saved (last <n> commits)
- <what changed, in human terms>

Staged, ready to commit
- <…>

Not saved yet
- <…>
```

Drop any section that is empty. If nothing is risky, drop the warning block entirely — do not manufacture a concern to fill it.
