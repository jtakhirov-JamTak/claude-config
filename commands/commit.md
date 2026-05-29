---
name: commit
description: Stage specific files and commit locally — pass `--push` to also push — never `git add -A`
---

Stage and commit changes. Default: commit only, no push. Pass `--push` (or `push`) in `$ARGUMENTS` to also push to the remote. Optional message hint can come as a separate arg.

Examples:
- `/commit` — stage + commit, no push
- `/commit --push` — stage + commit + push
- `/commit fix paywall race` — stage + commit with message hint, no push
- `/commit --push fix paywall race` — stage + commit + push with hint

## Step 1 — See what's changed

```
git status
git diff --stat
git log --oneline -5
```

Match recent commit style for tone, prefix conventions, and subject length.

## Step 2 — Stage explicitly

- **Never `git add -A` or `git add .`** — both stage everything including `.env*`, large binaries, accidental zip files, scratch files.
- Add files explicitly by path. Group by intent — if there are multiple unrelated changes, prefer multiple commits over one large one.
- Refuse to stage anything matching common sensitive patterns: `.env`, `.env.*`, `*.pem`, `*.key`, `credentials*`, `secrets*`, `*.p12`, `id_rsa*`. If one is in the diff, surface it explicitly and ask before proceeding.
- Refuse to stage anything > 10 MB without asking.
- Skip `node_modules/`, `dist/`, `.next/`, build artefacts, lockfile churn unrelated to a real dep change, and generated DB types unless the migration is in the same commit.

## Step 3 — Preview the stage

After staging, before committing:

```
git diff --cached --stat
```

Show the user what's about to be committed. If anything was *withheld* (sensitive pattern matched, large file, build artefact), state it explicitly — never silently drop a file.

## Step 4 — Write the message

- Subject ~50 chars, hard cap ~70, no trailing period.
- Match the project's prefix convention if there is one (`fix:`, `feat:`, `chore:`, numbered like `fix2:`).
- Body only if the *why* isn't obvious. Diff shows the *what*; the message captures the *why*.
- No marketing voice ("successfully", "comprehensive", "robust").
- Co-author trailer: ALWAYS end the message with the exact `Co-Authored-By:` trailer your current harness / system prompt mandates, verbatim, regardless of whether recent commits include one. Do not hardcode a model name in this file — the mandated string changes across versions and a pinned literal silently goes stale; read it from the current harness instructions each time.

## Step 5 — Commit

Single-line subject:

```
git commit -m "<subject>"
```

Multi-line body: this machine's default shell is PowerShell, which has **no bash heredoc**. Pass a single-quoted here-string to `-m` (open `@'`, close `'@` at column 0), or use the Bash tool for a real heredoc:

```
git commit -m @'
<subject>

<body line 1>
<body line 2>
'@
```

Don't skip hooks (`--no-verify`). If a pre-commit hook fails, the commit didn't happen — fix the underlying issue and create a new commit. Never `--amend` on hook failure.

## Step 6 — Push (only if `--push` in args)

If `$ARGUMENTS` contains `--push` or `push`:

```
git push origin <current-branch>
```

- Don't push to `main` if local has unreviewed history beyond the staged changes.
- Don't force-push.
- If push is blocked (no upstream, diverged history), report the actual git error verbatim — don't paraphrase.

If `--push` was not passed, end here and state explicitly: "Committed locally; not pushed. Run `/commit --push` to push."

## Step 7 — Confirm

Show: commit hash, subject, files changed, push status (pushed to `<remote>/<branch>` or "not pushed").
