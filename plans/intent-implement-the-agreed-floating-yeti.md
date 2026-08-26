# P0 template pass — agentic-template-v4

## Context

The template's governing metric is time from request → correct, green, usable feature.
Several things in it currently cost against that metric or are simply false:

- `.githooks/pre-commit` **fail-opens** when `package.json` exists but defines no
  `verify` script, while its own header claims "red code cannot be committed" — a claim
  a bypassable local hook cannot make (already tracked as `docs/BACKLOG.md` C7).
- `/interview` has one mode (new app). Every feature-sized change either pays a full
  three-phase interview or skips planning entirely.
- `CLAUDE.md`'s BUILD section is prose, so the build loop's stop conditions are a
  judgment call per session — the main source of unplanned human interruptions.
- Handoff state has two owners (`docs/PROGRESS.md` and `session-context.md`), and
  `docs/PROGRESS.md:3` points at a `progress-hygiene` skill that **does not exist**.
- `README.md` carries a v2→v4 changelog (git's job) and seven separately-verified false
  claims, including "CI" in the deterministic-layer table when `.github/` does not exist.
- Four `~/.claude/commands/add-*.md` files hold real failure-preventing knowledge and are
  already scheduled for deletion, gated on this session verifying the knowledge is
  extracted (`~/.claude/DECISIONS.md:89-93`).

Outcome: fewer interruptions, no false claims in the framework's own documentation, one
owner per concern, and `add-*` knowledge relocated so the four files can be deleted.

---

## The constraint that shapes execution

`scripts/hooks/write_guard.py:30`:

```python
GOVERNANCE = (".claude/", ".githooks/", "CLAUDE.md")
```

Edit/Write to any of those exits 2. Project `CLAUDE.md` backs it: "`.claude/`,
`.githooks/`, and this file change only via the human." Five of the ten files in scope
sit behind it. **The guard is not worked around.** Files split two ways:

| Applied by me directly | Applied by human (governance-locked) |
|---|---|
| `README.md` | `CLAUDE.md` |
| `.gitignore` | `.claude/commands/interview.md` |
| `docs/PROGRESS.md` | `.claude/skills/engineering-conventions/SKILL.md` |
| `docs/DECISIONS.md` | `.claude/rules/react-traps.md` *(new)* |
| `scripts/hooks/test_pre_commit.py` *(new)* | `.githooks/pre-commit` |

For the locked five I write complete final files into the scratchpad, plus **one**
PowerShell script that copies all five into place. After it runs, I re-read each
destination and compare SHA256 against the scratchpad source — one check that catches
BOM insertion and CRLF drift together (`.gitattributes` is `* text=auto eol=lf`).

Scratchpad root:
`C:\Users\jtakh\AppData\Local\Temp\claude\C--Users-jtakh-dev-agentic-template-v4\cedb5184-918f-4817-8f6d-502a08c51448\scratchpad`

Scratchpad files are written with the Write tool (BOM-less, LF) and copied with
`Copy-Item`, which is byte-exact and does not re-encode. No `Set-Content`, no `Out-File`.

---

## Step 5 result (settled before planning)

**Browser integration IS available** — `list_connected_browsers` returned one local
Chrome extension on Windows. So the visual-verification sequence goes into `CLAUDE.md`
rather than being deleted.

**One deviation, flagged:** `CLAUDE.md` is a *template* file copied into every new app,
possibly on machines without the extension. The sequence is written with a one-line
availability precondition instead of asserting the tools exist. Asserting unconditionally
would put an eighth false claim into the framework in the same pass that removes seven.

---

## Steps

### 1. `.githooks/pre-commit` — truthfulness + a real failure branch

Three explicit branches replacing the current two:

```bash
no package.json                 → echo, exit 0   (pre-foundation)
package.json, no verify script  → echo to stderr, exit 1
package.json with verify        → npm run verify
```

Header comment drops both false claims — "red code cannot be committed" and the
`shell_guard blocks repointing it` line (true on this machine only; the caveat already
lives in `CLAUDE.md`'s guardrails section) — and states instead: *pre-commit is fast local
drift control; CI is the backstop.*

**One addition beyond the literal ask, veto-able:** the current test is
`grep -q '"verify"'`, which matches `"verify"` anywhere — a dependency named `verify`
currently satisfies it. Replace with `node -e` parsing `scripts.verify`, falling back to
`grep -Eq '"verify"[[:space:]]*:'` when `node` is absent, printing which check ran. Adds
~6 lines; removes a branch that passes for the wrong reason.

### 1b. `scripts/hooks/test_pre_commit.py` *(new — not governance-locked)*

Follows the conventions already in `scripts/hooks/`: plain stdlib, no pytest, subprocess
invocation, exit-code assertions, `behaviour: N/N passed`, `main()` returns 1 on failure,
and a `--mutate` mode with a hardcoded `MUTATION_EXPECT_RED` set (per
`test_write_guard.py:27-40` — "a claim that updates itself cannot be wrong").

Runs `bash .githooks/pre-commit` directly in a temp cwd. It cannot go through a real
`git commit`: this repo's `core.hooksPath` is unset and the hook is mode `100644`
(`docs/BACKLOG.md` C4/C5), so the hook does not fire here at all. The test says so in its
docstring rather than implying coverage it does not have.

Cases: no package.json → 0 · package.json without verify → 1 · verify present, `npm` shim
exits 0 → 0 · verify present, shim exits 1 → 1 · `"verify"` present only as a dependency
key → 1. `npm` is a shim script on a prepended `PATH`, so cases are hermetic and fast.

Mutation: restore the fail-open branch (`exit 1` → `exit 0`); cases 2 and 5 must go red
and nothing else may.

### 2. `.claude/commands/interview.md` — two modes

Mode detection at the top: **no `docs/SPEC.md` → new-app mode; SPEC.md exists → feature
mode.** Feature mode that discovers a genuine architecture change escalates to full
DESIGN → SPECIFY but does **not** rerun or rewrite Part 1 unless the product outcome
itself changed.

Feature mode reads `docs/SPEC.md` and `docs/DECISIONS.md` first, then asks only what can
change *this* feature: behavior, flow, acceptance criteria, edge cases, data/API impact,
hard-to-reverse choices. Output amends SPEC.md with one feature entry —
behavior / acceptance criteria / non-goals / risks / evaluator triggers. Forbidden:
touching unrelated features or Part 1.

Kept intact from the current 84 lines: four-question batches, the stop rule, the no-build
test, inversion, delete/restore with the 10% rule.

Approval gates stated as numbers in the file:

| Work | Approvals |
|---|---|
| New app / architecture change | 2 — direction (incl. mockup if UI) + final SPEC |
| Feature | 1 — feature delta + mockup if UI |
| One-sentence reversible change | 0 — build directly |

**Conditional UI block**, fired only when the work adds or changes a screen. Exactly four
questions, one batch: primary user action · mobile-first / desktop-first / both ·
references (inspect `docs/mockups/<feature>/` first and use what is there) · which of
empty / loading / error / gated states matter. Then **one** mockup, not three: a thin
actual-stack page with hardcoded data on a branch if the frontend stack is settled,
otherwise the smallest reusable executable prototype. It rides in the direction approval.
Output is a short UI block inside the SPEC feature entry, not a separate document.

Note: `docs/mockups/` does not exist yet. The interview creates it on first use; no empty
scaffold directory is added.

### 3–4. `CLAUDE.md` — routing, build loop, production gate

**Routing** replaces "any feature that doesn't fit in one sentence" with the three-tier
rule from step 2. No `/add-*` references exist in this file to remove (verified: zero hits
in this tree — the `/add-*` routing was already stripped from `~/.claude/CLAUDE.md` in
`75c4b3d`). Global and project CLAUDE.md are checked for contradiction on when
`/interview` fires.

**BUILD** becomes the explicit loop:

```
For each SPEC feature:
  read requirements + acceptance criteria
  implement the thinnest correct version
  run the feature's acceptance checks
  red → diagnose, fix, rerun; do not ask
  evaluator trigger present → one evaluator run for the whole feature;
    fix P1 automatically; stop only for P0
  mark complete; immediately start the next feature; do not ask
```

Feature 1 is a walking skeleton — thinnest end-to-end usable path through UI → API → data
(→ auth if relevant). If dependencies make that impossible, Feature 2 must be. No
end-to-end path after Feature 2 → stop and amend SPEC.

Stop conditions during BUILD, exhaustively: material SPEC invalidation · irreversible
external action · a genuinely expensive-to-reverse decision the SPEC didn't settle ·
evaluator P0 · release/push · the delete/overwrite boundary **as defined in global
`~/.claude/CLAUDE.md`** (referenced, not restated — one owner).

**Production gate**, effect-based, the one exception to zero build-time approvals: *for
any app with real users (`pure-eq`), before executing any operation that can modify
existing production user data or change auth/RLS behavior — migration, repair script,
policy edit, anything — show it and wait.*

**Visual verification** (step 5, "yes" branch), added to the loop with its precondition:
start localhost → open the page at the target viewport → screenshot → compare against the
approved mockup → exercise one key state.

**Truthfulness fix in the same file:** the guardrails bullet "`.githooks/pre-commit` runs
`npm run verify`; red code cannot be committed" is corrected to match step 1.

### 6. Context — one owner

- `CLAUDE.md`: delete "Read `docs/SPEC.md` and `docs/PROGRESS.md` before touching
  anything" (PROGRESS half only) and the always-append-with-next-step rule.
  `session-context.md` is the only handoff; its trigger and format live in
  `~/.claude/commands/save-context.md` — referenced, not duplicated.
- `docs/PROGRESS.md` becomes shipped milestones + a metric log, one row per feature:
  `started_at · green_at · human_stops · rework · defects_after_green`. This is the
  instrument for the governing metric. The dangling `progress-hygiene` reference goes.
- `.gitignore`: add `session-context.md` (currently committable — nothing ignores it).
  **`.archive/` deliberately not added** per your answer; recorded in DECISIONS.md with
  the citation.
- **Confirmed, no edit:** `evaluator_guard.py:35` is
  `FORBIDDEN = ("progress.md", "session-context.md", "evals/")` and user-level
  `shell_guard.py:571` carries the same tuple. No filename changes here, so both stay
  correct. Neither file is touched.

### 7. Extract `add-*` knowledge, then hand back the delete list

Into `.claude/skills/engineering-conventions/SKILL.md` — only rules that prevent a
specific failure:

- `set_updated_at` trigger + its **ordering dependency** (the function must exist in an
  earlier migration or a fresh-DB apply fails)
- `archived_at` obligations (every list query, RLS SELECT policy, and export/deletion walk
  must filter on it, or archived rows leak or survive a deletion request)
- partial unique indexes (`WHERE archived_at IS NULL`) so an archived row does not reserve
  a name forever; and UNIQUE-index creation failing loudly by default over an arbitrary
  `rn > 1` dedup
- RLS policies in the same migration as the table
- handler ordering: origin/CSRF (mutating only) → auth → rate limit → validate → gate →
  idempotency → logic
- webhook order: raw body → signature → parse → replay defense → dispatch → mutate → ack,
  plus its inversions (no gate, no `req.json()` before verify, no 4xx on unhandled types)

Into `.claude/rules/react-traps.md` *(new)* — Strict-Mode double-invocation guard,
wizard-step component keying, `setState`-then-submit stale read, progressive save.

**Mechanism correction:** the frontmatter key is **`paths:`**, not `globs:` —
`.claude/rules/` is real and documented at
https://code.claude.com/docs/en/memory.md, and rules carrying `paths` load only when a
matching file is read. So:

```yaml
---
paths:
  - "**/*.tsx"
  - "**/*.jsx"
---
```

`.claude/rules/` does not exist in this tree yet; this creates it. Dropped in extraction:
workflow steps, "Verify" sections, confirmations, and anything already in
`~/.claude/REVIEWER_CONVENTIONS.md` §6 (which the `add-*` files cite rather than restate).

Then the four files are **listed as safe to delete** in the final output. I do not delete
them — they are outside this project, and `~/.claude/DECISIONS.md:89-93` gates deletion on
exactly this extraction. **One repair the deletion requires:**
`~/.claude/commands/new-app.md:3` names `/add-table, /add-endpoint, /add-page` in its
frontmatter description and is the only surviving external reference. Flagged for you;
not edited by me.

### 8. Evaluator triggers — text only

In `CLAUDE.md` and `interview.md`, "any migration" becomes:

- **always:** first vertical slice · auth/authz/RLS · money · destructive or
  data-transforming migration · migration touching existing production rows · any
  migration creating a table that will hold user data regardless of row count ·
  pre-release
- **not by default:** additive migration on a table holding no user data
- multiple triggers in one feature = **one** evaluator run

`.claude/agents/evaluator.md` and both hook scripts are **not touched** — frozen per the
B2 decision, and `test_evaluator_guard.py:93-213` pins ~20 contract assertions against
that file's frontmatter and body strings.

### 9. `README.md` — remove history, remove false claims

Remove the "v4 changes (from v2)" section (`:7-48`). Drop "CI" from the layer table
(`:53`) — `.github/` does not exist. Collapse the B2 story to a one-line pointer to
`docs/DECISIONS.md`; it is currently told five times in this file alone.

Plus the four additional false claims (your answer: fix all seven):

| Line | Claim | Reality |
|---|---|---|
| `:13` | "Rules live in `CLAUDE.md` (35 lines)" | 65 lines |
| `:73` | "all three hook entries" | `settings.json` has one |
| `:92` | "`shell_guard.py` **is registered** for `Bash\|PowerShell`" | contradicted by its own blockquote 3 lines below; the template ships no such file |
| `:211,:213` | residual gaps numbered `4.` twice | five items numbered 1–4 |

### 10. Re-resolve every citation

Before reporting, re-resolve every backticked command, path, and skill name in every file
touched, **against the tree it belongs to** — this repo for project paths, `~/.claude` for
user-level ones. Report anything that does not resolve. Known live examples to confirm
survive the edits: `engineering-conventions`, `evaluator`, `docs/evals/`,
`env.example` (no leading dot), `~/.claude/commands/save-context.md`,
`docs/mockups/<feature>/`.

---

## DECISIONS.md entries added

1. **Template-maintenance sessions pay five manual copies.** `write_guard.py` locks
   `.claude/`, `.githooks/`, `CLAUDE.md`; a session that edits the framework itself
   therefore hands files to the human. Accepted — the framework-freeze rule makes these
   sessions rare. **Put-back trigger:** more than two maintenance sessions in one month →
   design a maintainer mode. Do not weaken the guard before then.
2. **Mockup kill criterion.** After three UI-bearing features, if mockup approval has not
   reduced post-build UI rework, delete the mockup step.
3. **Evaluator trigger scope.** ~20 optional evals with zero unique P0/P1 → narrow. Two
   serious defects escaping unevaluated work → broaden.
4. **Pre-commit is drift control, not a trust boundary** — with the `node`-parse choice
   and its residual limit (fallback grep still cannot separate `scripts.verify` from a
   dependency named `verify`).
5. **`.archive/` deliberately absent from `.gitignore`**, citing `~/.claude/DECISIONS.md`
   2026-08-25: archiving was deleted as ceremony and nothing produces that directory.
6. **Visual verification is conditional on browser tooling being present**, because
   `CLAUDE.md` ships to machines that may not have it.

---

## Verification

Ordered, and each check names what would turn it red.

1. **Byte fidelity of the five copied files.** After you run the copy script, SHA256 of
   each destination vs its scratchpad source. *Red if:* any hash differs — that is a BOM
   or CRLF conversion, and `.gitattributes` (`* text=auto eol=lf`) would then fight it on
   every commit.
2. **`python scripts/hooks/test_pre_commit.py`** → all cases pass.
   **`python scripts/hooks/test_pre_commit.py --mutate`** → cases 2 and 5 go red, nothing
   else does. *Red if:* the mutation leaves everything green, which would mean the test
   asserts nothing about the fail branch.
3. **Existing suites still green** — `python scripts/hooks/test_write_guard.py`,
   `--mutate`, and `python scripts/hooks/test_evaluator_guard.py`. *Red if:* an edit
   disturbed a governance path or an evaluator contract string. These must be green
   *because* the plan claims neither guard was touched.
4. **The write guard still blocks its own governance paths** — after the copies land, one
   Edit attempt against `CLAUDE.md` must still exit 2. *Red if:* it succeeds, meaning the
   guard was disarmed somewhere in the process.
5. **Citation resolution** (step 10) — every backticked path resolves in the correct tree.
6. **`git status --porcelain`** at the end lists only the ten intended files. *Red if:*
   anything else moved.
7. **No commit, nothing staged.** Confirmed by `git status` output at the end.

Not verified by this plan, and stated as such: whether the pre-commit hook fires on a real
commit in a derived app. It cannot fire in *this* repo (`core.hooksPath` unset, mode
`100644`), and fixing that is `docs/BACKLOG.md` C4/C5, out of this intent.

---

## Out of scope — stated so it is not mistaken for done

- `.claude/agents/evaluator.md`, `evaluator_guard.py`, `write_guard.py`,
  `test_evaluator_guard.py`, `test_write_guard.py` — frozen (B2, recorded put-back
  trigger).
- Creating any `shell_guard.py` in this repo — it is user-level by decision.
- Deleting the four `~/.claude/commands/add-*.md` files, or editing
  `~/.claude/commands/new-app.md:3` — outside this project; handed to you as a list.
- The hook mode bit / `core.hooksPath` (`BACKLOG` C4/C5).
- Any commit or push.
