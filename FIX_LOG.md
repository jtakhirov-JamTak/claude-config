# Fix Log — the config set itself

Defects in this repository: the rules, commands, hooks, and permission config. Format
per the fix-log rule in `CLAUDE.md`. Newest first.

### 2026-08-19 — The destructive-git denies never matched the form actually in use

**Problem:** `Bash(git reset --hard:*)`, `Bash(git clean:*)` and the two force-push rules
match on a **command prefix**. The ordinary way to operate on another repository is
`git -C <path> clean -fdx`, whose prefix is `git -C` — so no rule matches and the command
runs. The protection had been believed effective since it was committed this morning
(`efda...`), and every `git -C` call made during that session went through unguarded.
Compounding it: the claim "Bash denies this, PowerShell bypasses it" was asserted without
ever running the Bash form, and the test offered as proof used `git -C`, so it
demonstrated the argument-position gap rather than the shell gap it was cited for.

**Fix:** PowerShell copies of the four denies added, and `PowerShell(git *)` removed from
the allow list in `settings.local.json` — an allow rule skips the auto-mode classifier
entirely, so destructive git in that shell had no guard of any kind. The `git -C` gap is
**deliberately left open**: prefix rules cannot express "git, any path, then clean", and
closing it exactly would need a blocking hook, which is a pattern rejected for other
reasons. With the allow rule gone, that form now reaches the classifier instead.

**Regression test:** Proven by mutation in both directions rather than by reading the
config. Denied: `cd ~/.claude && git clean -n` under Bash, and the `Set-Location`
equivalent under PowerShell. Still runs: `git -C ~/.claude clean -n` under both. Dry-run
(`-n`) only — the destructive form was deliberately not run against a live repository, so
whether the classifier stops it is **unverified**.

**Found in:** this repo, while verifying a fix the user requested — not by the review that
introduced the rules.
