---
name: new-app
description: Scaffold a new app from the agentic-template-v4 GitHub template — create the repo, wire the pre-commit hook, verify the Python interpreter, and hand off to /interview. Use when starting a brand-new app. NOT adding a feature to an existing app (use /add-feature); NOT a second branch of current work (use /worktree).
---

Scaffold a new app from the template. App name: $ARGUMENTS

The template is `jtakhirov-JamTak/agentic-template-v4`. This command creates the
repo, makes the guardrails actually load, and stops — planning happens in
`/interview`, in a fresh session, inside the new directory.

Shell is PowerShell 5.1: chain with `;` or `if ($?) { ... }`, never `&&` or `||`.

## Step 0 — Location

Run from the dev root `C:\Users\jtakh\dev`, never from `C:\Users\jtakh` itself —
a session started at the home directory loads no project `CLAUDE.md`.

Confirm the app name is not already taken:

```
Test-Path "C:\Users\jtakh\dev\<name>"
```

If it exists, stop and ask. Do not overwrite.

## Step 1 — Create the repo from the template

```
gh repo create <name> --template jtakhirov-JamTak/agentic-template-v4 --private --clone
```

Private by default. If the human wants it public, they say so — public is
effectively irreversible once indexed.

## Step 2 — Point git at the template's hooks

```
cd <name> ; git config core.hooksPath .githooks
```

Without this, `.githooks/pre-commit` never runs and red code can be committed.
Verify it took:

```
git config core.hooksPath
```

## Step 3 — Make the pre-commit hook executable

Windows git checks the file out non-executable, and CI/WSL/macOS silently skip
non-executable hooks. The template's files are already tracked after a
`--template --clone`, so set the bit directly and commit it:

```
git update-index --chmod=+x .githooks/pre-commit ; git commit -m "chore: mark pre-commit hook executable"
```

Confirm the mode is `100755`:

```
git ls-files -s .githooks/pre-commit
```

## Step 4 — Verify the interpreter the hooks call

The three PreToolUse hooks invoke `python` by name. If only `py` resolves on
this machine, every hook dies silently and the guardrails are decorative.

```
python --version
```

If that fails, patch `"command": "python"` to `"command": "py"` in
`.claude/settings.json` — all three hook entries — and re-check.

## Step 5 — Confirm the guardrails loaded, then hand off

Do not report success on the basis of the commands above exiting 0. Say plainly
which of these you checked and which you did not:

- `core.hooksPath` reads back as `.githooks`
- `.githooks/pre-commit` is mode `100755`
- `python --version` printed a version

Then print, verbatim:

> Scaffold ready. Start `claude` in this directory, Shift+Tab into Plan Mode,
> and run `/interview <your app idea>`.

Hook and permission checks that need a live session — `/hooks`, `/permissions`,
and the deny-rule spot checks in the template README — belong to that next
session, not this one. Say so rather than claiming they passed.
