# Session A — correctness / guards

## Context

Handoff `ABC.md` v2.2 specifies four fixes to the guard layer shared by
`~/.claude` (user-level config) and `dev/agentic-template-v4` (app template).
Session A only; B/C/D are out of scope.

I reproduced all three defects against the live files first. They are real and
worse than the handoff describes:

**A1 — git global-option bypass (P0 by the handoff's own kill criteria).**
11 of 13 destructive forms exit 0 through `shell_guard.py` *and* through the
`permissions.deny` prefix rules, which are also prefix-matched and so miss the
same forms:

```
exit=0  git -C repo reset --hard          exit=0  git -c core.hooksPath=/tmp/x commit -m y
exit=0  git -C repo clean -fd             exit=0  git --config-env=core.hooksPath=EVIL commit
exit=0  git -C repo push --force          exit=0  git --work-tree=/tmp/r checkout -- .
exit=0  git -C repo commit --no-verify    exit=0  GIT_CONFIG_COUNT=1 ... git commit -m y
exit=0  git -C "C:/path with spaces/repo" reset --hard      (PowerShell form too)
```

The two forms that *did* block did so by accident, not coverage:
`git --git-dir=/tmp/r/dotgit reset --hard` → exit 2 only because the regex
`git\s+reset\s+--hard` matched inside the **path text** `dotgit reset --hard`.
Change the path and it opens: `git --git-dir=/srv/repo reset --hard` → exit 0.
So the current guard has a false negative *and* a false positive from the same
line-oriented matching.

**A2 — MultiEdit secret bypass, confirmed.** `scan_secrets.py` joins only
`content`/`new_string`/`new_str`/`file_text`. A secret in `edits[].new_string`
exits 0 while the identical secret in `Write.content` exits 2.

**A3 — `isolation: worktree` is worse than stated.** Docs confirm the worktree
is branched "from your default branch rather than the parent session's HEAD".
The evaluator therefore misses uncommitted work *and* can miss committed work
on a feature branch — it may be grading a tree that never existed.

**A4 — BOM.** `~/.claude/.gitignore` starts `EF BB BF` and contains two
mojibake em-dashes (`â€”`). `new-app.ps1:139` writes `.claude/settings.json`
with `Set-Content -Encoding utf8`, the PS 5.1 BOM-producing path.

### One discovery that changes the A3 design

A2 says "delete the Python Read-hook branch"; A3 says the evaluator must be
blocked from *reading* PROGRESS.md. Those looked contradictory. They are not:
subagent frontmatter supports a `hooks:` field scoped to that agent only
(verified in the sub-agents reference). The evaluator gets its own Read guard;
the main session keeps **zero** processes on the Read path, satisfying both A2
and the "ordinary Read → 0 custom processes" kill criterion.

---

## A1. Git command normalization

**Files:** `~/.claude/hooks/shell_guard.py`, `~/.claude/hooks/test_shell_guard.py`,
plus byte-identical copies at `dev/agentic-template-v4/scripts/hooks/` (they are
identical today; keep them so — B2 may delete the template copy later, but until
it does the template must not ship a guard proven bypassable).

Replace line-oriented regex matching of git commands with a **parse → normalize
→ match** pipeline. Per the handoff, no `segment.split()`.

**Tokenizer.** `shlex.split(segment, posix=False)` — `posix=False` is the
correct mode here because it does not treat `\` as an escape, so
`C:\path with spaces\repo` survives, and it keeps quote characters attached so
quoted-ness is recoverable per token. Strip one matching quote layer after
tokenizing. Unbalanced quotes on a git segment → **fail closed** (block with a
parse message), matching the existing evaluator behaviour.

**Normalization.** For each segment whose command word is `git`:

1. Consume leading `NAME=VALUE` env assignments into `env{}`, then expect `git`.
2. Consume git global options until the first non-option token (the subcommand).
   Handle both spellings: `--opt=value` and `--opt value`, and the value-taking
   set `-C -c --git-dir --work-tree --namespace --exec-path --config-env
   --super-prefix`. Collect them into `globals[]`.
3. Emit a normalized string `git <subcommand> <remaining args>` with the globals
   removed and originally-quoted argument bodies blanked.

Match the existing `GIT_RULES` against that normalized string. This is what makes
the required discrimination fall out for free rather than being enumerated:

- `git -c color.ui=false status` → `git status` → ALLOW
- `git -C "C:\path with spaces\repo" reset --hard` → `git reset --hard` → BLOCK

It also removes the phantom `--git-dir=.../dotgit` match, because path text is
no longer scanned as if it were the command.

**Policy on the collected globals/env** (over-blocking is a framework defect, so
this is deliberately narrow — chosen answer: block only when it defeats
something):

- BLOCK when any global or env sets `core.hooksPath` by any spelling —
  `-c core.hooksPath=…`, `--config-env=core.hooksPath=…`, or
  `GIT_CONFIG_KEY_n=core.hooksPath`. Applies regardless of subcommand, because
  repointing hooks is the bypass itself.
- BLOCK when `GIT_DIR` / `GIT_WORK_TREE` / `--git-dir` / `--work-tree` / `-C`
  redirect a **destructive** subcommand (the normalized form already decides
  this — the existing `GIT_RULES` fire).
- ALLOW otherwise: `GIT_DIR=x git status`, `git -c color.ui=false status`,
  `git -C repo diff --stat`, `git reset HEAD file`.

Non-git segments keep the current `BASH_RULES` / `PS_RULES` path unchanged.

Also update the module docstring: it currently says agent identity "may" arrive
as `agent_type` and cites `isolation: worktree` as the backstop. `agent_type` is
documented, `agent_name` is not, and after A3 the worktree backstop no longer
exists — the docstring must say so.

### Tests (both directions, per case)

Add to `test_shell_guard.py`, keeping every existing case:

BLOCK — `-C`, `-c`, `--git-dir`, `--work-tree`, `--config-env`, `GIT_CONFIG_*`,
`GIT_DIR`, `GIT_WORK_TREE`, each against `reset --hard`, `clean -fd`,
`push --force`, `commit --no-verify`, `checkout -- .`; quoted Windows paths
containing spaces; each in the PowerShell form; each after a Bash `&&` chain and
inside `$(...)`.

ALLOW — `git -C "C:\path with spaces\repo" status`, `… diff --stat`,
`git -c color.ui=false status`, `git reset HEAD file`, `git status`, `git log`,
`GIT_DIR=x git status`, ordinary single-file delete, and every existing ALLOW
case unchanged.

### Mutation test

`test_shell_guard.py --mutate` copies the guard to the scratchpad, neuters the
normalization step to an identity passthrough, runs the full suite against the
**mutant**, and asserts:

- every label in the expected git-global set turns red, and
- **no other label changes state**.

Named expected set, so it fails in both directions: if the fix stops working the
mutation stops distinguishing anything, and if the fix over-blocks, an unrelated
ALLOW label flips and the assertion fails. No production kill-switch is added —
the mutation is textual, on a temp copy.

---

## A2. One write guard

**Create:** `dev/agentic-template-v4/scripts/hooks/write_guard.py`
**Delete:** `scripts/hooks/protect_paths.py`, `scripts/hooks/scan_secrets.py`
**Update:** `.claude/settings.json`

Matcher becomes `Edit|Write|MultiEdit` with **one** hook process. The `Read`
matcher block is deleted entirely — `permissions.deny` is the hard Read layer,
which is also the only layer that survives `@file` mentions.

Carry over from `protect_paths.py` unchanged: secret-file paths (`.env*`,
`*.pem`, `id_rsa*`, `id_ed25519*`), governance paths (`.claude/`, `.githooks/`,
`CLAUDE.md`), forward-only migrations (Edit/MultiEdit always blocked; Write
blocked only when the file exists, so a new migration is allowed).

Content scanned across `content`, `new_string`, `new_str`, `file_text`, **and
every `edits[].new_string`** — the gap that is currently open.

Secret classes: the existing eight, plus `whsec_…`, `\b(sk|rk)_(test|live)_…`,
`sntrys_…`, and `postgres(ql)?://user:password@host`. Stripe `pk_` publishable
keys are explicitly **not** blocked; `\b(sk|rk)_` cannot match inside `pk_test_`,
which the ALLOW cases assert directly.

`env.example` allowed / `.env` blocked are both already true and get tests. The
existing `.env.example` / `.sample` / `.template` exception stays — collapsing it
is B3 and out of scope.

### Tests — `test_write_guard.py`

Write safe · Edit safe · MultiEdit safe · secret in `Write.content` · secret in
`Edit.new_string` · secret in the **first**, **middle**, and **last**
`edits[]` entry · each new secret class · `pk_test_` and `pk_live_` allowed ·
governance file blocked · existing migration blocked · new migration allowed ·
`env.example` allowed · `.env` blocked · `.env.example` allowed.

### Mutation test

`--mutate` removes the `edits[]` traversal and asserts **exactly** the
MultiEdit-secret labels turn red, with every other label unchanged.

---

## A3. Evaluator uses the real working tree

**Update:** `.claude/agents/evaluator.md`, `CLAUDE.md`, `scripts/hooks/shell_guard.py`
**Create:** `scripts/hooks/evaluator_guard.py`, `scripts/hooks/test_evaluator_guard.py`

Remove `isolation: worktree`. Keep `tools: Read, Glob, Grep, Bash` — no Edit, no
Write. Add agent-scoped frontmatter hooks:

```yaml
hooks:
  PreToolUse:
    - matcher: "Read|Grep|Glob"
      hooks:
        - type: command
          command: "python scripts/hooks/evaluator_guard.py"
```

`evaluator_guard.py` blocks `docs/PROGRESS.md`, `session-context.md`, and
`docs/evals/**`, and allows everything else. It re-checks `agent_type` itself
rather than trusting registration alone, so it is inert if it ever fires
elsewhere.

`shell_guard.py`'s evaluator branch gains the same three path denies, because
`cat` is on the evaluator allowlist and would otherwise read straight past the
Read guard.

Rewrite the evaluator's isolation paragraph: the worktree sentence is now false
and must go. Replace with the porcelain protocol — first and final command is
`git status --porcelain` (**not** `--untracked-files=no`, which hides new
untracked files), both recorded verbatim in the report. The main session records
its own `git status --porcelain` immediately before dispatch. Invariant:

```
main-session before  =  evaluator first  =  evaluator final
```

Any difference invalidates the evaluation. `git diff HEAD --stat` stays as
evidence but is not a substitute.

Template `CLAUDE.md` EVALUATE step gains the record-porcelain-before-dispatch
instruction.

### Tests

Script-level, deterministic (`test_evaluator_guard.py` + shell-guard cases):
PROGRESS.md read blocked · session-context.md read blocked · `docs/evals/**` read
blocked · `docs/SPEC.md` and source reads allowed · same three blocked via shell
· shell writes blocked · non-allowlisted command blocked · `git status
--porcelain` allowed · identical payload with a non-evaluator `agent_type`
passes (proves the block is agent-scoped, not global).

Structural: parse `evaluator.md` and assert `isolation` absent, `tools` contains
no `Edit`/`Write`, hook registered.

Live (one dispatch, authorized): scratch git repo, one committed file, one
**uncommitted** edit, one untracked file. Dispatch the evaluator; assert it
reports content only visible in the uncommitted edit, and that
`git status --porcelain` is byte-identical before and after. This is also the
only way to verify the frontmatter hook actually fires and that a relative
`command:` path resolves — `${CLAUDE_PROJECT_DIR}` is **not** documented for
subagent hooks. If it does not fire, that is a blocking finding, not a fix to
improvise around.

---

## A4. PowerShell 5.1 BOM

**Update:** `~/.claude/new-app.ps1`, `~/.claude/CLAUDE.md`, `~/.claude/.gitignore`

`new-app.ps1:139` — replace `Set-Content -Encoding utf8 -NoNewline` with an
explicit no-BOM write:

```powershell
$full = (Resolve-Path $settings).Path
[System.IO.File]::WriteAllText($full, $patched, (New-Object System.Text.UTF8Encoding($false)))
```

(`.NET` resolves relative paths against the process directory, not PowerShell's
`$PWD`, so the absolute path is required, not cosmetic.)

Then assert in-script, replacing the current parse-only check: JSON still parses
**and** the first three bytes are not `EF BB BF`. Fail loudly on either.

`~/.claude/CLAUDE.md` "This machine" — replace the current
"Write files with `-Encoding utf8`" sentence, which is the instruction that
caused this, with the handoff's wording:

> PowerShell 5.1 `-Encoding utf8` writes a BOM. For source/config files, prefer
> Claude Write/Edit tools. Do not use `Set-Content` or `Out-File` for
> settings/config files unless encoding is explicitly safe.

`~/.claude/.gitignore` — strip the BOM and repair the two mojibake em-dashes.
Content is otherwise untouched; I will show the byte-level before/after.

### Verification

First, prove the premise can fail: write a probe file both ways in the
scratchpad and `xxd` the first three bytes. `Set-Content -Encoding utf8` must
show `EF BB BF` and the `WriteAllText` path must not. If the probe does not
reproduce the BOM on this machine, A4's premise is wrong and I stop and report
rather than "fixing" a non-problem.

Then: run the patch step against a copy of the template's `settings.json`,
assert no BOM and `ConvertFrom-Json` parses. Full `/new-app` end-to-end needs a
real GitHub repo and touches the automatic-commit behaviour that C5 removes —
out of scope; I will say so rather than claim scaffold coverage.

---

## Out of scope — recorded, not done

Findings that surfaced during A but belong to B/C/D or later, appended to
`docs/BACKLOG.md`:

- `.githooks/pre-commit` is mode `100644` at template source (C4/C5).
- Template `permissions.deny` `Bash(git reset:*)` over-blocks `git reset HEAD
  file`, and prefix rules miss every `-C`/`-c` form the A1 hook now catches —
  the deny list and the hook disagree (B4).
- `pre-commit` comment and template `CLAUDE.md` both claim "red code cannot be
  committed" (C7).
- `format-after-edit.ps1` still registered PostToolUse in `~/.claude/settings.json` (B1).
- Duplicate template shell guard remains until B2.

---

## Verify

```powershell
python C:\Users\jtakh\.claude\hooks\test_shell_guard.py
python C:\Users\jtakh\.claude\hooks\test_shell_guard.py --mutate
python C:\Users\jtakh\dev\agentic-template-v4\scripts\hooks\test_shell_guard.py
python C:\Users\jtakh\dev\agentic-template-v4\scripts\hooks\test_write_guard.py
python C:\Users\jtakh\dev\agentic-template-v4\scripts\hooks\test_write_guard.py --mutate
python C:\Users\jtakh\dev\agentic-template-v4\scripts\hooks\test_evaluator_guard.py
```

Then: settings JSON parses on both repos, no BOM; one live evaluator dispatch
with porcelain equality; `git status` on both repos shown as a diff.

**No commit, no push.** Final report: full diff, test output, and the
disagreements below.

## Disagreements to raise with the outcome

1. **`postgres://user:password@host` as a blocked secret class** is specified,
   but it blocks the exact placeholder form that belongs in docs and
   `env.example`. Implementing as specified; flagging that it will produce false
   positives on documentation, which the handoff's own criteria call a framework
   defect.
2. **A3's read-blocks are partial by construction.** The evaluator keeps `Bash`
   with `git diff` allowed, so PROGRESS.md content remains reachable via a diff.
   The guard narrows the path, it does not close it; the report should not claim
   otherwise.
