---
name: worktree
description: Create a git worktree for parallel work, with the env files and untracked dev state copied across
---

Create a git worktree so you can work on a feature in parallel without disturbing the current branch. Worktree name: $ARGUMENTS

A bare `git worktree add` will produce a directory that compiles but can't actually run, because the worktree gets the tracked files only — no `.env*`, no local migrations cache, no `node_modules`. This command handles that.

## Step 1 — Survey

```
git branch -a
git worktree list
git status
```

- If the current worktree has uncommitted changes that should travel with the new branch, decide whether to commit them first, stash them, or leave them behind.
- Confirm the worktree name doesn't already exist.

## Step 2 — Choose the path

Place the new worktree at a sibling of the current repo, not inside it. Default to `../<repo-name>-<worktree-name>`. Confirm the parent directory exists.

## Step 3 — Create the branch and worktree

```
git worktree add ../<repo-name>-<arg> -b feature/<arg>
```

If a branch with that name already exists, fail loudly — don't silently check it out and risk diverging from a previous worktree.

## Step 4 — Carry untracked dev state

These files are gitignored on purpose, but the new worktree won't be runnable without them. Copy from the source worktree:

- `.env`, `.env.local`, `.env.development.local`, `.env.production.local`, and any other framework-specific env files in use (`.envrc`, `.env.example` stays in git — skip).
- Any project-specific local config not in git (e.g. `supabase/.temp/`, `.vercel/`, `.firebase/`, `.netlify/`).

For each: if it exists in the source, copy to the new worktree. List what was copied.

Do **not** copy: `node_modules/`, `.next/`, `dist/`, `build/`, `.turbo/`, any other build cache. They're large and may be platform- or hash-specific. The user should run `npm install` (or equivalent) in the new worktree.

## Step 5 — Install + verify

Recommend (don't run unless the user asks) the install command for the project (`npm install`, `pnpm install`, `bun install`, etc.) so the new worktree has its own `node_modules`.

## Step 6 — Confirm

Report:
- New worktree path
- New branch name
- Env files copied (list each)
- Files NOT copied that the user may need (anything in `.gitignore` that wasn't on the carry list)
- One-line instructions for the user: open a second editor / Claude session at the new path; merge back when done. PowerShell has no `&&` operator — chain with `;` + `if ($?)`:
  - PowerShell: `git checkout <main>; if ($?) { git merge feature/<arg> }; if ($?) { git worktree remove ../<repo-name>-<arg> }`
  - Bash: `git checkout <main> && git merge feature/<arg> && git worktree remove ../<repo-name>-<arg>`

## Notes

- Worktrees share the same `.git/` — don't run destructive git operations (`gc`, `prune`, `reflog expire`) from one while the other is active.
- A worktree's branch can't be checked out in two places at once. If a sibling worktree is on the same branch, you'll get an error.
