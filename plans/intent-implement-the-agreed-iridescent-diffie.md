# P0 config pass — `~/.claude`

## Context

This repo is the global Claude Code config: rules (`CLAUDE.md`), 30 command files, a
shell guard hook, a statusline, and a scaffold script. It has accumulated three kinds of
drag on the governing metric (request → correct, green, usable feature):

1. **Interruptions from over-broad rules.** `CLAUDE.md:11` ("show me what something is
   before you delete or overwrite it") fires on every routine edit to tracked source,
   which git already makes reversible.
2. **Tool overhead every turn.** `statusline.ps1` spawns a full PowerShell process and
   shells out to `git` on every render, to print seven fields when one is load-bearing.
3. **Stale/duplicated config.** A `/resume` command that collides with a Claude Code
   built-in; a `save-context` procedure with archiving, category detection and pruning
   that a one-intent-per-session rule makes dead weight; an `autoMode.environment` block
   that describes `C:\Users\jtakh` as the trusted repo; a `/add-feature` router over four
   commands; `new-app.ps1` making two unrequested commits.

Intended outcome: fewer interruptions, a cheaper statusline, and no config that describes
a world that no longer exists. Plus a kill criterion so this framework work is bounded.

**Scope discipline:** no commits, nothing staged. Every decision lands in `DECISIONS.md`.

---

## Verified before planning

| Claim in the brief | Status |
|---|---|
| `/resume` collides with a built-in | **Confirmed.** `claude --help` line 129: "shown in the prompt box, **/resume picker**, and terminal title". |
| `context_window.used_percentage` is the field | **Confirmed.** `statusline.ps1:32` already reads exactly it. |
| `claude auto-mode config/critique/reset` exist | **Confirmed** via `claude auto-mode --help`. |
| `autoMode.environment` is stale | **Confirmed.** It states `C:\Users\jtakh` has "no git remotes and 0 tracked files" and is the "Trusted repo" — but `.claude` under it is a 46-file git repo. |
| `new-app.ps1` makes commits | **Confirmed** at `:110` and `:159`. |
| `new-app.md` references `.env.example` | **FALSE.** Neither `new-app.md` nor `new-app.ps1` contains that string. Real hits: `deploy-check.md:64`, `deploy-check.md:182`, `worktree.md:37`. Handled under step 8b. |
| `/resume` refs are in save-context, CLAUDE.md, README, DECISIONS | **Partly false.** Only `save-context.md:3` and `:11`. `CLAUDE.md` has zero. There is no `README.md`. `DECISIONS.md` has zero. |
| Delete rule came from an incident | **FALSE.** Introduced new in `dc1ac75` with no ancestor; `FIX_LOG.md` has zero delete/overwrite incidents. Its only load-bearing citation is `DECISIONS.md:62`. |
| `auto-mode reset` only clears `environment` | **FALSE.** It removes the whole `autoMode` section. Settings.json is therefore not hand-edited for auto mode. |

---

## Steps

### 1. Kill criterion

`DECISIONS.md` — insert immediately after the `# Decisions` H1, before the existing
preamble:

> **Framework freeze: if config/template commits exceed 1 per 5 app commits for two
> consecutive weeks without a verified P0/P1 incident, framework work stops.**

### 2. `/resume` → `/resume-context`

- `git mv commands/resume.md commands/resume-context.md`
- `resume-context.md:2` — `name: resume` → `name: resume-context`
- `save-context.md:3` and `:11` — `/resume` → `/resume-context`
- Nothing else in the repo references it. `CLAUDE.md`, `DECISIONS.md`: no change; no
  `README.md` exists.

### 3. Collapse `save-context` / `resume-context` to six sections

`commands/save-context.md` — rewrite. New trigger line at the top:

> Run this when the statusline shows context ≥ 45%, when intent changes, or after two
> consecutive failed fixes. Then `/clear`, then `/resume-context`.

`session-context.md` becomes exactly these six sections and nothing else:
`Current goal` / `Verified state` / `Done this session` / `Files changed` /
`Unresolved risk` / `Exact next action`.

Delete: Step 0 first-run category seeding, Step 1 `.archive/` + 20-snapshot retention,
Step 2 category detection, Step 3 detected-sections-only update, Step 6 14-day prune
prompt, and all multi-project handling. Update the frontmatter description, which
currently advertises "archiving and category detection".

`commands/resume-context.md` — match the six-section format. **Keep the file/symbol
verification step** (every path in `Files changed` still exists, symbols grep-confirm) —
that is the part that earns the file's existence. The 14-vs-7-day stale asymmetry
resolves itself: the 14-day prune is gone; the 7-day `[STALE]` flag stays.

### 4. Statusline → Python, context only

New `statusline.py`:
- Read stdin, `json.loads`, print `Context NN%` from `context_window.used_percentage`.
- Default color < 45%, yellow ≥ 45%, red ≥ 60%.
- Never crash and never write a traceback to stdout: bad/empty JSON, missing
  `context_window`, or null percentage → treat as 0. Clamp to 0–100.
- Nothing else. No model, cost, git branch, folder, or bar.

`settings.json` — replace the `statusLine` block:
```json
"statusLine": {
  "type": "command",
  "command": "python C:/Users/jtakh/.claude/statusline.py"
}
```
**Deviation, deliberate:** the brief says "the same Python launcher pattern the hooks
use." The hooks use a `command` + `args` array split; `statusLine` currently uses a
single command string and that form is proven working. I keep the launcher (`python`,
which resolves to `C:\Python314\python.exe`) and the proven single-string shape rather
than introduce an unverified key into the one thing that renders every turn.

Then `git rm statusline.ps1`. Its full contents are already on screen above in this
session, satisfying the show-before-delete stop.

**Measurement (step 9 reports both numbers).** Sample payload written to the scratchpad,
10 invocations each, same shell, mean wall-clock. Target < 100 ms.
**Stop condition:** if Python's mean is ≥ 100 ms, report the number and stop — no further
optimization.

### 5. Auto mode — commands for you, no settings edit

Per your call, `settings.json`'s `autoMode` block is **not** touched; `reset` removes the
whole section itself.

`CLAUDE.md` has no `## Permissions` section, so the rule goes under `## This machine`:

> - Add an Auto-mode trust entry only after the same legitimate operation is denied
>   twice. Smallest possible entry.

### 6. Narrow the delete/overwrite hard stop

**Provenance, as requested:** there is no incident. `git log -S` puts the line's birth at
`dc1ac75` ("docs: rewrite CLAUDE.md as a pruned, trigger-phrased rule set"), where it
appears as a new line with no ancestor — the prior file had only "Never delete data with
history value". That commit's message documents provenance for its other new rules and
says nothing about this one. `FIX_LOG.md` has zero delete/overwrite incidents.

**The one real citation:** `DECISIONS.md:59-64` names this rule as the compensating
control for an accepted gap — "the hook blocks recursive deletes, not single-file ones…
A single-file delete is therefore governed by the `CLAUDE.md` hard stop behaviourally,
not mechanically."

Replace `CLAUDE.md:11` with the mechanical form you specified:

> - **Never ask before editing, deleting, renaming, or refactoring tracked source as part
>   of an approved task** — git makes it reversible. Ask before:
>   - deleting or overwriting any file that is **untracked, or tracked with uncommitted
>     changes** (`git status` is the test — not a judgment about who created it);
>   - destructive git history operations;
>   - any operation that modifies existing production data or changes auth/RLS behaviour;
>   - irreversible external actions;
>   - anything involving money;
>   - files outside the project;
>   - materially changing an approved SPEC.

Then amend `DECISIONS.md:59-64` to cite the new clause instead of the deleted line, and
add one sentence recording that the original rule had no incident behind it (`dc1ac75`,
no ancestor) so the next reader does not go hunting for one.

*Note:* this turns a one-line hard stop into ~9 lines inside `## Hard stops`. Flagging the
shape; implementing in place as specified.

### 7. Delete `/add-feature`

- `git rm commands/add-feature.md`
- `CLAUDE.md:95` — drop `, `/add-*`` from the command-set pointer list.
- **Collateral the brief did not name:** `add-endpoint.md:3`, `add-page.md:3` and
  `new-app.md:3` all point at `/add-feature` in their frontmatter descriptions. Deleting
  the target without fixing these leaves three dangling links — the exact LINK-RESOLVE
  failure `REVIEWER_CONVENTIONS.md` §6 names. I fix all three descriptions in the same
  pass.
- `add-table` / `add-endpoint` / `add-page` / `add-webhook` are **kept**, with a
  `DECISIONS.md` line recording they are scheduled for deletion once Session 2's
  extraction is verified.

### 8a. `new-app.ps1` — no commits, preflight first

**Remove both commits:**
- `:110-111` — `git commit -m 'chore: mark pre-commit hook executable'` and its check.
  Safe: `git update-index --chmod=+x` writes the **index**, and the verification at `:113`
  reads `git ls-files -s`, which also reads the index. The 100755 check still passes
  without a commit. (Stated because if it didn't, this removal would break the check.)
- `:158-159` — keep `git add $settings` (staging is fine), delete the `git commit`.

**Move preflight ahead of repo creation.** Currently Step 0 (name, dev root, `gh`, `git`,
name-free-on-GitHub) runs before `gh repo create`, but the interpreter check is Step 4 —
*after* the repo exists. Split it:
- **Step 0 gains** the interpreter *detection* (fail loudly if neither `python` nor `py`
  resolves) and a **template-reachability** check (`gh repo view` on
  `jtakhirov-JamTak/agentic-template-v4`, using the same `EAP=Continue` + `$LASTEXITCODE`
  pattern already at `:75-82` — that idiom exists because a plain `2>$null` there killed
  the script; do not reintroduce it).
- **Step 4 keeps only the patch**, which cannot move: it edits the *new* repo's
  `.claude/settings.json`, which does not exist until after the clone.

**Stage-tracking.** `commands/new-app.md:24` currently says the script "does not
half-scaffold" → replace with "stops at the first failure and reports which stages
completed." That sentence is only true if the script actually reports it, so `Fail` gains
a printed list of completed stages. Doc and code change together.

### 8b. `env.example` (the defect step 8 was reaching for)

`.env.example` is blocked as secret-shaped by `hooks/shell_guard.py:75` and
`test_shell_guard.py:241`; `env.example` is the supported non-secret file. Three lines
still say otherwise:
- `commands/worktree.md:37` — "`.env.example` stays in git — skip" → `env.example`
- `commands/deploy-check.md:64` and `:182` → `env.example`

Plus a `DECISIONS.md` line: `env.example` is canonical, `.env.example` is blocked by
design, so the next command file does not reintroduce it.

### 9. Output

A table of every changed file with its one-line reason; the before/after statusline
timing numbers; the three auto-mode commands for you to run; and the `DECISIONS.md`
entries added. Then stop.

---

## `DECISIONS.md` additions

One dated `### 2026-08-25 — P0 config pass` heading with one bullet per decision
(what / why / put-back trigger), which satisfies "one line each" without breaking the
file's newest-first H3 convention. Plus the separate in-place amendment at `:59-64`.

Covered: `/resume-context` rename · six-section session context · Python statusline with
its measured numbers · delete-rule replacement + no-incident note · `env.example`
canonical · `add-feature` deleted / four `add-*` scheduled · auto-mode trust entries only
after two denials.

**Put-back trigger for every removed statusline field:** it goes back only when you say
you missed it.

---

## Verification

Each check below names the input that would turn it red.

**Statusline correctness** — pipe crafted payloads to `statusline.py`:

| Input | Expected | Red if |
|---|---|---|
| `used_percentage` 0, 20 | default color | any color code emitted |
| 44 / 45 | default / **yellow** | boundary off by one |
| 59 / 60 | yellow / **red** | boundary off by one |
| 100 | red, `Context 100%` | clamp fails |
| `{}` (no `context_window`) | `Context 0%` | traceback or crash |
| empty stdin / `not json` | `Context 0%` | traceback on stdout |

**Statusline timing** — 10 runs each, same shell, sample payload from the scratchpad.
Red if Python's mean ≥ 100 ms → report and stop.

**Live render** — after the `settings.json` edit, the statusline must actually show
`Context NN%`. Red if the bar is blank or shows a PowerShell error, which is what a
`command`-shape mistake would look like.

**`new-app.ps1`** — `powershell -File new-app.ps1` with (a) an invalid name, (b) a name
that already exists on GitHub. Both must fail **at Step 0 with no repo created**, and
print the completed-stages list. Red if `gh repo create` runs first, or if the stage list
is absent (which would make the new `new-app.md` sentence false). Full-path scaffold is
**not** run — it creates a real GitHub repo.

**Link integrity** — `grep -rn "/add-feature\|/resume\b\|\.env\.example" *.md commands/`
must return zero hits outside `FIX_LOG.md`/`DECISIONS.md` history text. Red if any command
file still points at a deleted target.

**Hook still armed** — `settings.json` parses and the `hooks` block is byte-unchanged.
Red if the statusline edit disturbed it.

**Tree state** — `git status` shows modifications and renames, **zero commits**, nothing
staged beyond what `git mv`/`git rm` inherently stage. Red if `git log` moved.

**After you run `claude auto-mode reset`** — re-check that `statusLine` survived the
CLI's rewrite of `settings.json`.
