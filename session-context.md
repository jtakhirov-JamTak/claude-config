# Session Context

Updated: 2026-08-25 21:28 (UTC)

## Current goal

Cut framework friction in `~/.claude`: narrow rules that fired on safe work, make the
statusline cheap, and delete config describing a world that no longer exists. Done meant
everything committed and pushed with the guard suite green.

**Reached.** Four commits pushed, tree clean, `origin/master` = `85c1500`. Nothing is in
flight. The next session picks a new intent rather than resuming this one.

## Verified state

- `python hooks/test_shell_guard.py` → **249/249 passed**. Was 218/218 at session start.
- `python hooks/test_shell_guard.py --mutate` → **11/11 mutations**, each turning exactly
  its named set red and nothing else.
- Statusline timed 3×10 runs on a payload asserted to parse under both `json.loads` and
  PowerShell `ConvertFrom-Json` first: `statusline.ps1` **505 ms/render**,
  `statusline.py` **97 ms**, bare `python -c pass` floor **69 ms**.
- Shell-guard hot-path cost, 20 runs each: old **161 ms/call**, new **142 ms** — no
  regression.
- `settings.json` after the auto-mode CLI rewrote it: valid JSON, no BOM, 0 CRLF,
  `statusLine` and the `hooks` registration both intact, `autoMode` absent.
- `claude auto-mode config` vs `claude auto-mode defaults` → `allow`/`soft_deny`/
  `hard_deny`/`environment` all match defaults.
- `git fetch` + rev-parse compare: local and `origin/master` identical, tree clean.
- Repo visibility via `gh repo list`: `pure-eq`, `you-inc`, `agentic-template-v4`,
  `claude-config` are **PUBLIC**; `the-leaf-v2`, `PurePath`, `TheLeaf` private.
- `/interview`, `write_guard.py`, `evaluator_guard.py` all confirmed present and tracked
  in `dev/agentic-template-v4` — I had wrongly called all three dangling.
- **Not verified:** the `new-app.ps1` happy path was never run end to end; it creates a
  real GitHub repo. Only its two preflight failure paths were exercised.
- **Not verified:** that the narrowed `CLAUDE.md` delete rule reduces prompts in
  practice. No before/after count was taken.

## Done this session

- `75c4b3d` P0 config pass — delete/overwrite rule narrowed to a `git status` test;
  statusline PowerShell→Python; `/resume`→`/resume-context`; save/resume-context cut to
  six sections; `/add-feature` deleted with its three orphaned links repaired;
  `new-app.ps1` stripped of two unrequested commits, preflight moved ahead of repo
  creation; `env.example` naming corrected.
- `3f8a36e` shell guard — payload vs operand (heredoc and here-string bodies no longer
  parsed as commands), plus two pre-existing defects it exposed: **newline was not a
  command separator**, so `npm test\nrm -rf ./src` and `npm test\ngit reset --hard` were
  allowed; and `tee .env` / `dd of=.env` wrote secrets unblocked.
- `da2cc4c` auto-mode reset to shipped defaults.
- `85c1500` `PROJECTS.md` — added the template repo and a Visibility column.

## Files changed

Still on disk:

- `hooks/shell_guard.py` — payload stripping, newline separator, `\b` on file-rule verbs, `tee`/`dd` rule
- `hooks/test_shell_guard.py` — 31 new cases, 4 new mutations
- `CLAUDE.md` — delete/overwrite rule replaced; auto-mode trust rule added; `/add-*` routing removed
- `DECISIONS.md` — framework-freeze kill criterion; two new entries; two amendments
- `FIX_LOG.md` — two new entries
- `PROJECTS.md` — template row + Visibility column
- `statusline.py` — new
- `settings.json` — statusLine repointed; `autoMode` removed
- `.gitignore` — `statusline.ps1`→`statusline.py`; `__pycache__/` and `*.pyc` added
- `new-app.ps1`, `commands/new-app.md`, `commands/save-context.md`,
  `commands/resume-context.md`, `commands/add-endpoint.md`, `commands/add-page.md`,
  `commands/deploy-check.md`, `commands/worktree.md`

Deleted on purpose — `/resume-context` should expect these to be absent:

- `statusline.ps1`, `commands/resume.md` (renamed), `commands/add-feature.md`

## Unresolved risk

- **`pure-eq` is PUBLIC and is the only app with real users.** Its history has not been
  audited for committed secrets. This is the highest-value open item.
- `claude-config` is PUBLIC. `settings.json` history (predating this session) contains an
  inventory of sensitive-looking paths under home — paths, not credentials, and permanent
  in history.
- `dev\app-foundation` is listed in `PROJECTS.md` as not-found: no repo of that name on
  the account, no local directory. Row kept, marked, awaiting your call to retire it.
- A private `TheLeaf` repo exists; its relationship to `the-leaf-v2` is unconfirmed.
- `the-leaf-v2` state still reads "first workshop April 2026", four months past.
- The `.env.example` cross-layer disagreement (auto-mode default calls such templates
  committable; `shell_guard.py` blocks reading them) is real but **inert** — no dotted
  `.env.example` exists in any project or in the template.
- Two of my own checks produced clean-looking results that measured nothing, both caught
  and logged in `FIX_LOG.md`: the statusline benchmark ran on unparseable JSON so both
  scripts were timed on their error path; and the first word-boundary test rows were
  heredoc-wrapped, so stripping alone made them pass. **Failure mode to watch: a green
  result, not an error.**
- Three "dangling reference" calls were wrong because I searched only inside `~/.claude`.
  The template is the blind spot; the new `PROJECTS.md` row exists to prevent a repeat.

## Exact next action

In `C:\Users\jtakh\pure-eq`, audit the full git history for committed secrets, because
it is PUBLIC and has real users:

```
git -C ~/pure-eq log --all --diff-filter=A --name-only --pretty=format: | sort -u | grep -Ei '\.env|secret|credential|\.pem|\.key'
git -C ~/pure-eq log --all -p -- '.env*' | head -100
```

If anything sensitive appears, **rotate the credential first** — rewriting history does
not recall what has already been cloned or indexed. Then decide whether the repo should
be public at all.
