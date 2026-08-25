# Decisions — the config set itself

**Framework freeze: if config/template commits exceed 1 per 5 app commits for two
consecutive weeks without a verified P0/P1 incident, framework work stops.**

Kept verbatim with the numbers that settled them, per the decisions rule in `CLAUDE.md`.
Read this before re-attempting anything recorded as rejected. Newest first.

### 2026-08-25 — P0 config pass

One line per decision: what, why, and what would put it back.

- **`/resume` renamed to `/resume-context`.** `/resume` is a Claude Code built-in (its
  own `--help` names the "/resume picker"), so the authored command was shadowed. Put
  back only if the built-in is retired.
- **`session-context.md` is six fixed sections, overwritten whole.** Archiving, the
  20-snapshot retention, category detection and the 14-day prune all assumed multiple
  concurrent intents per repo; one-intent-per-session already rules that out, so they
  were pure ceremony. Put back if a session ever legitimately needs two live intents.
- **`/resume-context` keeps its verification step.** It is the only part that can turn
  red — a restored context that is quietly wrong is worse than none. Never remove.
- **Statusline is Python and prints context percentage only.** Measured 3×10 runs each,
  same shell, on a payload gated through both parsers first: `statusline.ps1` **505
  ms/render** (with its git-branch cache warm — its best case), `statusline.py` **97
  ms/render**, against a bare `python -c pass` floor of **69 ms**. So 5.2× faster, ~408
  ms saved per render, and only 28 ms of what remains is this script — the rest is
  CPython startup, which is why the target was met but only by 3 ms and no further
  optimisation was attempted. Model, cost, git branch, folder and the progress bar were
  dropped. Put back any single field only when you say you missed it.
  *The first measurement of this was wrong and is recorded here so the mistake is not
  repeated: the sample payload contained `"C:\Users\..."`, which is invalid JSON, so both
  scripts took their parse-failure path and PowerShell never made its git call. It read
  424 ms vs 90 ms. Any timing harness for a stdin-parsing script must first assert the
  fixture parses.*
- **Delete/overwrite hard stop narrowed to a `git status` test.** The old rule fired on
  every routine edit to tracked source, which git already makes reversible; it had no
  incident behind it (`dc1ac75`, no ancestor). Put back if an ungated delete of a
  tracked-and-clean file ever loses something that mattered.
- **`env.example` is the canonical name; `.env.example` is blocked by design.**
  `hooks/shell_guard.py` treats every `.env*` as secret-shaped, so a command file telling
  you to maintain `.env.example` describes a file the guard will refuse to read. Fixed in
  `deploy-check.md` and `worktree.md`. Do not reintroduce the dotted form in a new command.
- **`/add-feature` deleted; `/add-*` routing removed from `CLAUDE.md`.** It was a router
  over three commands that each already say what to run next. `add-table`,
  `add-endpoint`, `add-page` and `add-webhook` are **kept for now and scheduled for
  deletion once Session 2 verifies their knowledge has been extracted** — do not delete
  them before that verification.
- **`new-app.ps1` makes no commits.** It made two unrequested ones, against the standing
  never-commit-unless-asked rule. The mode bit and any settings patch are left staged;
  the `100755` check still verifies through the index, so nothing was weakened. Put back
  never.
- **`new-app.ps1` preflights the interpreter and template before creating the repo.** A
  failure after `gh repo create` leaves a real GitHub repo behind. The settings *patch*
  necessarily stays in Step 4 — it edits a file that does not exist until the clone.
- **Auto-mode trust entries require two denials.** Recorded as a rule in `CLAUDE.md`; the
  stale `autoMode` block is cleared by `claude auto-mode reset`, not by hand.

### 2026-08-23 — The scaffold lives in `new-app.ps1`; the command delegates to it

**Decision:** `new-app.ps1` is the single definition of the scaffold.
`commands/new-app.md` runs it and reports; it does not restate the steps.

**Why the script and not the command.** A session binds its project root at
launch, so a `/new-app` run from the dev root cannot load the app it just
created — it needed a second session. Running the scaffold in the terminal
first and launching `claude` once, inside the new folder, removes that entirely.
The command still exists for when you want the checks run for you.

**Rejected — keeping the steps in both places.** Two copies of six commands
drift the moment one changes, and the command was already the stale copy once
(it told you to verify `core.hooksPath` with a read the guard then blocked).

**On `/cd`:** it can rebind a session's project root — documented. Whether hooks
and permission rules follow the rebind is **not** documented, so neither file
suggests it. Fresh launch inside the app instead.

**The interpreter check is not ceremony.** Hooks fail open on their own errors by
design, so a missing `python` makes the guardrails decorative rather than
loudly broken. The script fails hard there, and patches `settings.json` to `py`
if that is what resolves.

### 2026-08-23 — `shell_guard.py` installed as a user-level PreToolUse hook

**Decision:** the command guard written for the app template now also runs
machine-wide, registered in `settings.json` for `Bash|PowerShell`.

**Context.** A `/permissions` review turned up that `permissions.deny` matches a
command *prefix*, so `Bash(rm -rf:*)` covers `rm -rf x` and nothing else — not
`rm -fr x`, not `rm -r -f x`, not `cd s ; rm -rf x`. Checking the five real
projects then showed the bigger problem: `pure-eq`, `the-leaf-v2`, `you-inc`,
`PurePath` and `dev/app-foundation` have **zero** deny rules and no command
guard between them (app-foundation has a Stop-typecheck hook and nothing else).
The only protection in those repos was the 12 user-level denies, which contain
no `rm` or `Remove-Item` entry at all. `pure-eq` has real users.

**Rejected — adding prefix denies to the user file.** Two lines, but it inherits
the exact weakness that caused the problem: it would describe one spelling of
`rm`, not the capability. A rule that misses `rm -fr` is worse than no rule,
because it reads as coverage.

**Rejected — per-project installs.** Five copies of the same script to keep in
sync, and it leaves any future repo unprotected until someone remembers.

**Accepted — one user-level hook.** Parses the command instead of prefix-matching
it, so flag order, flag splitting, abbreviation, PowerShell aliasing and
position in the line all stop mattering. Covers every repo including ones that
do not exist yet. The template keeps its own copy so a scaffolded app stays
self-contained; the two files are byte-identical and both carry the 87-case
test.

**Known limit, accepted:** the hook blocks recursive deletes, not single-file
ones. Blocking every delete would fire constantly on temp files and would make
the test suite's ALLOW column meaningless. A single-file delete is therefore
governed behaviourally, not mechanically, outside a template-derived project.
Re-open if a single-file delete ever destroys something that mattered.

**Amended 2026-08-25.** The `CLAUDE.md` hard stop this entry cited — "show me what
something is before you delete or overwrite it" — no longer exists. The behavioural
control is now the narrower clause that replaced it: *ask before deleting or overwriting
any file that is untracked, or tracked with uncommitted changes*. That still covers this
gap, because the single-file delete worth fearing is the one git cannot undo. Deletes of
tracked-and-clean files are deliberately no longer gated. For the record, the original
rule had no incident behind it — `git log -S` puts its birth at `dc1ac75` as a new line
with no ancestor, and `FIX_LOG.md` contains no delete/overwrite entry. Do not go looking
for one.

### 2026-08-23 — `hooks/stop-typecheck.ps1` stays dormant and unregistered

**Decision:** the file stays on disk, stays out of `settings.json`, and is not
deleted. It is parked, not orphaned — this entry is the record that says so.

**Context.** A config review flagged it as an orphan (present in `hooks/`, absent
from `settings.json` `"hooks"`) and offered register-or-delete. Its own header
already answers that: *"Deliberately dormant. Do NOT wire this up on principle — a
hook that blocks the end of a turn is the pattern that has caused trouble before."*

**Rejected — registering it.** The evidence trigger is named and specific:
repeatedly shipping type errors. That has not happened. A Stop hook returning a
wrong verdict blocks the end of a turn, and the only escape is Claude Code's
8-consecutive-block override — a cost paid on every false positive against a
benefit that is currently hypothetical.

**Rejected — deleting it.** The implementation is complete and carries reasoning
that would have to be re-derived: script discovery over a hardcoded
`npm run typecheck` (only one of five projects has that script), Stop rather than
PostToolUse (per-edit typechecking flags intentionally incomplete mid-refactor
states), and exit 2 for self-correction. Deleting costs that; keeping it costs
nothing but the file.

**Re-open when:** type errors reach a commit twice. Then register it per the
wiring snippet in the file header, and record the trigger event here.

### 2026-08-19 — Prune `CLAUDE.md`; do not reorder it

**Decision:** `CLAUDE.md` is maintained by pruning against per-line necessity — *would
removing this line cause a mistake?* Section order is chosen for human readability only,
and no adherence claim may be made for it.

**Rejected — reordering as an adherence lever.** A full reorder was built and measured:
sections regrouped under trigger-phrased headers (`Hard stops`, `When two fixes have
failed`), prohibitions moved to the top, on the theory that a header matching the
situation is a better retrieval key. **No published evidence supports this, and the entire
file is in context every turn, so there is no retrieval step for ordering to improve.** It
also grew the file — 130 lines against a 106-line committed baseline — because a
self-imposed three-bullet section cap forced nine sections into fifteen, and headers are
bloat. Abandoned. Do not rebuild it.

**Accepted — pruning.** 106 → 90 lines, 1004 → 777 words. Every cut is either covered by a
file that is actually consulted (`dev/app-foundation/docs/FIX_LOG.md` carries the
`spawnSync` fix in three entries; `docs/RUNBOOK_RESTORE.md` carries the restore drill; the
template `.gitignore` carries the Claude-local-state rule) or replaced by a shorter form
that cannot go stale — "anything tracked here" instead of an enumeration of tracked files.
Shipped as `dc1ac75`. One sentence was dropped without a home: the `/commit` ≡ "commit and
push" equivalence guarantee, whose intent survives as *"invoke it as a skill instead of
improvising."*

**Kept from the reorder,** on readability grounds only: trigger-phrased headers and
one-idea-per-bullet. Plus `IMPORTANT` / `NEVER` / `YOU MUST` emphasis on the hard stops —
that one *is* officially documented to improve adherence, and neither earlier version of
the file used it.

**Also rejected — "the harness already covers it" as grounds to cut.** Three of eight cuts
in the first pruning pass were justified by the rule appearing in Claude Code's own base
prompt: PowerShell `&&`/`||`/ternary, `Set-Content` ANSI defaults, and "match the
surrounding code." Two were reinstated. The base prompt genuinely does contain them —
verified by quoting tokens (`Add-Content`, `null-coalescing`, "system ANSI codepage") that
appear zero times across every authored file here, so the reading was not self-referential.
It is rejected anyway on dependency grounds: that prompt is unversioned, cannot be diffed,
and changes with every CLI update. Moving enforcement of the highest-frequency rules onto
it trades a file under version control for one that cannot be read reliably. The PS 5.1
pin is additionally machine-specific in a way a generic prompt cannot carry — `&&` works
in PowerShell 7.
