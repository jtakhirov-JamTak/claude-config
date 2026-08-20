# Fix Log — the config set itself

Defects in this repository: the rules, commands, hooks, and permission config. Format
per the fix-log rule in `CLAUDE.md`. Newest first.

### 2026-08-19 — A result was stated as fact before the test that would establish it was run

**Problem:** The claim "`git clean` is denied under Bash, and PowerShell bypasses that
deny" was reported as an established finding. The Bash half had never been run — it was
inferred by reading `settings.json`. The PowerShell half *was* run, but with
`git -C <path> clean -n`, a form no rule matches in **either** shell, so "it ran" was
equally true of Bash and demonstrated nothing about shells. A diagnosis, a proposed fix,
and a security narrative were built on top of it, and the user acted on the conclusion.
The defect is not the wrong guess. It is delivering a read-and-reasoned conclusion in the
same voice as a measured one, which leaves the reader no way to tell which they are
being given.

**Fix:** No code change; this is behavioural. The guard already existed —
`CLAUDE.md` §Verification, *"never state something as fact because a note said it… check
the code, run the query"* — committed at 15:02 the same day. It did not prevent the
failure at ~16:30. A rule loaded into every session that still does not fire is the same
shape as `VACUOUS-PASS`: present, cited, and measuring nothing. What actually changed the
outcome was the user asking for proof instead of accepting the claim.

**Regression test:** **None exists, and that is the honest state.** No mechanical gate
catches an unverified assertion in prose. The nearest usable discipline is the one the
same day's `VACUOUS-PASS` upgrade demands of tests: name the command that was run and
show its output, so that a claim arriving with no command attached is visibly different
from one that has. Whether that holds is unmeasured.

**Found in:** this repo, by the user asking for proof rather than accepting the claim.

### 2026-08-19 — The destructive-git denies never matched the form actually in use

**Problem:** `Bash(git reset --hard:*)`, `Bash(git clean:*)` and the two force-push rules
match on a **command prefix**. The ordinary way to operate on another repository is
`git -C <path> clean -fdx`, whose prefix is `git -C` — so no rule matches and the command
runs. The protection had been believed effective since it was committed that morning
(`efda...`), and every `git -C` call made during that session went through unguarded.

**Fix:** PowerShell copies of the four denies added, and `PowerShell(git *)` removed from
the allow list in `settings.local.json` — an allow rule skips the auto-mode classifier
entirely, so destructive git in that shell had no guard of any kind. The `git -C` gap is
**deliberately left open**: prefix rules cannot express "git, any path, then clean", and
closing it exactly would need a blocking hook, a pattern rejected for other reasons. With
the allow rule gone, that form now reaches the classifier instead.

**Regression test:** Proven by mutation in both directions rather than by reading config.
Denied: `cd ~/.claude && git clean -n` under Bash, and the `Set-Location` equivalent under
PowerShell. Still runs: `git -C ~/.claude clean -n` under both. Dry-run (`-n`) only — the
destructive form was deliberately not run against a live repository, so whether the
classifier stops it is **unverified**.

**Found in:** this repo, while verifying a fix the user requested — not by the review that
introduced the rules.
