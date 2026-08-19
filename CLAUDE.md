# Global Instructions

Applies to every project unless a project-level CLAUDE.md says otherwise.

## Environment

- Windows 11, PowerShell is the primary shell. Bash is available but takes POSIX syntax.
- PowerShell 5.1: no `&&`, no `||`, no ternary. Chain with `;` or `if ($?) { ... }`.
- Never work directly out of `C:\Users\jtakh` — it is the home directory, not a project.
  Start in the project folder so its CLAUDE.md loads and searches stay scoped.

## Working style

- Lead with the answer. Keep explanations short; expand only when asked.
- If a fix isn't working after ~3 attempts, stop and say so rather than trying
  progressively more speculative changes.
- Flag security and data-loss risks proactively, even when unasked — assume I will
  not spot them myself.
- Before deleting or overwriting anything, show me what it is first.

## Code

- Match the conventions already in the file. Don't introduce a new pattern for a
  problem the codebase has already solved somewhere else.
- Don't add comments explaining what the code plainly does.
- Never commit or push unless I ask.
- Secrets belong in `.env` files only, never in source, logs, or committed docs.

## Active projects

| Path | What it is | State |
|---|---|---|
| `pure-eq` | Insights app | **Live — the only shipped app.** |
| `the-leaf-v2` | Leaf — the main product | In build; MVP polish, first workshop April 2026 |
| `dev\app-foundation` | Shared scaffolding / reference architecture | Reference only, never deployed |
| `you-inc` | Scoring + pricing app | Early |
| `PurePath` | Habit / sprint app | Early |

All five are git repos pushed to `github.com/jtakhirov-JamTak`. Only `pure-eq` has
users, so "is this safe to ship" means something different there than in the rest.

## This directory is versioned

`~/.claude` is itself a git repo (branch `master`) holding the authored skill set.
The `.gitignore` denies everything at the root and re-includes only the authored
files, so runtime state, transcripts, and `.credentials.json` can never be tracked.
After changing a command, an agent, `REVIEWER_CONVENTIONS.md`, or this file, commit
it — an uncommitted skill set is the one thing here with no backup.

## Custom commands

`~/.claude/commands` holds an authored review and scaffolding set (`/review-changes`,
`/full-review`, `/grill`, `/deploy-check`, `/add-*`, etc.). Prefer these over generic
equivalents — they encode project-specific conventions. Shared review conventions and
the rules for maintaining the set: `~/.claude/REVIEWER_CONVENTIONS.md`.
