---
name: new-app
description: Scaffold a new app from the agentic-template-v4 GitHub template by running ~/.claude/new-app.ps1. Use when starting a brand-new app. NOT adding a feature to an existing app (use /add-feature); NOT a second branch of current work (use /worktree).
---

Scaffold a new app from the template. App name: $ARGUMENTS

The scaffold is defined in one place — `~/.claude/new-app.ps1`. Run it; do not
restate or re-implement its steps here, and do not "helpfully" run the
underlying git/gh commands yourself. One canonical definition is the point.

## Run it

```
powershell -NoProfile -ExecutionPolicy Bypass -File C:/Users/jtakh/.claude/new-app.ps1 <name>
```

Pass `-Public` through only if the human explicitly asked for a public repo.

The script preflights the name locally and on GitHub, creates the repo from the
template, wires `core.hooksPath`, sets and verifies the `100755` bit on
`.githooks/pre-commit`, and checks that the interpreter the hooks invoke
actually resolves — patching `settings.json` to `py` if that is what exists. It
fails loudly on any of those; it does not half-succeed.

## Report

Relay what the script printed. Say plainly which things it verified
(`core.hooksPath`, pre-commit mode, interpreter) and which it could not:
**hook registration and permission rules need a live session in the new folder,
and this session is not it.** Do not claim those passed.

## Then stop

Tell the human to launch `claude` in the new directory themselves — and say why,
because it looks like pointless ceremony otherwise:

- A session binds its project root at launch. Project `CLAUDE.md`,
  `.claude/settings.json` and the hooks all resolve against that root, so this
  session cannot load a project that did not exist when it started.
- `/cd` can rebind the project root — that much is documented — but whether
  hooks and permission rules follow the rebind is **not** documented. Do not
  rely on it. A fresh launch inside the app costs seconds and removes the
  question.
- A trust dialog appears on first launch. If it is declined, none of the project
  hooks or permission rules load.

Then give them the canary, which is the first thing worth doing in that session:

> Ask Claude to read `.env`. It must be **denied**. If the read succeeds, the
> project settings did not load — stop and fix that before building anything.

After the canary passes: Shift+Tab into Plan Mode, run `/interview <app idea>`.
