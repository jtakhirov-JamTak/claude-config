# Decisions — the config set itself

Kept verbatim with the numbers that settled them, per the decisions rule in `CLAUDE.md`.
Read this before re-attempting anything recorded as rejected. Newest first.

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
governed by the `CLAUDE.md` hard stop behaviourally, not mechanically, outside a
template-derived project. Re-open if a single-file delete ever destroys
something that mattered.

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
