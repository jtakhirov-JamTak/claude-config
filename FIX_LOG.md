# Fix Log — the config set itself

Defects in this repository: the rules, commands, hooks, and permission config. Format
per the fix-log rule in `CLAUDE.md`. Newest first.

### 2026-08-23 — `new-app` could never scaffold anything: a stderr redirect under EAP=Stop

**Problem:** `new-app Compass` died in Step 0 with `NativeCommandError` from
`gh repo view`. The cause was not `gh` and not GitHub — it was line 65 of `new-app.ps1`:

    gh repo view "jtakhirov-JamTak/$Name" 2>$null | Out-Null
    if ($?) { Fail "A GitHub repo named '$Name' already exists." }

PowerShell 5.1 wraps a native command's stderr in `ErrorRecord`s **when that stderr is
redirected**, and `$ErrorActionPreference = 'Stop'` (line 31) turns those into a
*terminating* error. `gh repo view` writes to stderr on the good path — the repo does not
exist — so the script aborted at the exact moment it had proved the name was free. The
script was unrunnable in both directions: a free name threw, and a taken name hit `Fail`.
Every scaffold since the redirect was introduced would have failed the same way. This is
the exact pitfall already written down in `CLAUDE.md` under "This machine"
(*"Avoid `2>&1` on native executables"*), applied to `2>$null`.

**Fix:** Drop `$ErrorActionPreference` to `Continue` around the probe, merge stderr into
the pipeline instead of the null device, and read `$LASTEXITCODE` — the only reliable
signal — then restore the previous preference:

    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    gh repo view "jtakhirov-JamTak/$Name" 2>&1 | Out-Null
    $repoExists = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEap
    if ($repoExists) { Fail "A GitHub repo named '$Name' already exists." }

`$?` was checked at each of lines 78/87/99/102 too; those follow *unredirected* native
calls, and a native command writing to stderr with no redirect leaves `$?` `True`
(verified), so they are sound and were left alone.

**Regression test:** The check now has a failure mode, which the old one did not — it
threw before it could decide anything. Run the block at `$ErrorActionPreference = 'Stop'`
over two names and assert both directions:

    Compass              -> $repoExists = False   (free; must NOT throw)
    agentic-template-v4  -> $repoExists = True    (taken; must trip Fail)

`agentic-template-v4` is the input that turns it red; without it a check that always
returns False looks green. Verified in both directions on 2026-08-23. Manual, not
hook-enforced — that is the honest state.

**Related, verified not firing:** `python --version 2>&1` (line 128) and
`py --version 2>&1` (line 143) are the same construct under the same `EAP=Stop`. Both
interpreters on this machine write the version to stdout, so neither throws today; an
interpreter build that emits a warning to stderr would kill the scaffold the same way.

**Found in:** the user's terminal, first real run of `new-app`.

### 2026-08-19 — A coverage check drew its criteria from the artifact it was checking

**Problem:** `CLAUDE.md` was restructured rather than edited, and the rewrite was verified
by extracting ~35 distinctive rule anchors and grepping each against the result. It
returned 35/35. Seven rules were missing at that moment: "preserve user input when a
request fails", the backup drill timing, the open fix field on a stopped attempt, the
`Out-File` BOM caveat, the named command list, `.credentials.json`, and the prohibition on
inferring schema from type files or an earlier conversation. The check passed because the
anchors were chosen *from the rewrite*, so every one was present by construction. It was
not a weak check — it had no failure mode. The user found all seven by diffing the two
files by hand.

**Fix:** Two changes, both shipped in `dc1ac75`. `CLAUDE.md` gained a rule with no ancestor
in the previous version: verification must be able to fail, and a check's criteria must
come from the source, the spec, or the original — never from your own output. §6 of
`REVIEWER_CONVENTIONS.md` gained `SELF-ANCHORED-CHECK`. The mechanical form is a
token-level diff anchored to the original: every code span and content word in the source,
tested for presence in the result. Rerun that way, the same check surfaced
`.credentials.json` immediately — same task, same two files, one variable changed.

**Regression test:** `SELF-ANCHORED-CHECK`'s audit question is the usable discipline —
before trusting a green result, name the concrete input that would have turned it red. For
file restructuring specifically the token-level diff is mechanical and repeatable. Neither
is enforced by a hook; both are conventions, and that is the honest state.

**Found in:** this repo, by the user diffing the restructured file against the original.

### 2026-08-19 — One inspection was reported as covering three repositories

**Problem:** While adding `.gitattributes` to four repos, `you-inc` was staged and its
renormalisation scope inspected — `.gitattributes` only, no content change. The identical
command was then applied to `PurePath` and `the-leaf-v2` in a single batch and committed
**and pushed** without inspecting either. `the-leaf-v2` behaved differently: 12 files
carried CRLF blobs in the index and were rewritten. The outcome was benign — verified
content-identical afterwards with `git diff --ignore-cr-at-eol` — but that was luck, not
process. The commit message generated for all three asserts *"the index was already LF …
this changes no stored content"*, which is false for `the-leaf-v2` and is now permanent in
`c453a52`, since correcting it would require a force-push.

**Fix:** No code change; behavioural, and the same class as the entry above. One inspection
covering three targets cannot distinguish them — the check had no way to return a different
answer per repo. `pure-eq` was then staged, inspected on its own, and committed with a
message accurate to what its own diff showed (`ac76bd9`).

**Regression test:** None mechanical. The discipline: a per-target claim needs a per-target
observation, and a commit message asserting what a diff contains must be written *after*
reading that diff. `PATTERN-REPEATS` covers deriving the class from one instance; this is
its inverse — do not assume the members of a class behave uniformly without checking each.

**Found in:** this repo, by reading the diffstat after the push had already gone out.

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
