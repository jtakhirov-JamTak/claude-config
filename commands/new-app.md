---
name: new-app
description: Scaffold a new app from the agentic-template-v4 GitHub template by running ~/.claude/new-app.ps1. Use when starting a brand-new app. NOT adding a feature to an existing app (use /interview from inside that app — it detects feature mode from an existing docs/SPEC.md); NOT a second branch of current work (use /worktree).
---

Scaffold a new app from the template. App name: $ARGUMENTS

The scaffold is defined in one place — `~/.claude/new-app.ps1`. Run it; do not
restate or re-implement its steps here, and do not "helpfully" run the
underlying git/gh commands yourself. One canonical definition is the point.

## Run it

```
powershell -NoProfile -ExecutionPolicy Bypass -File C:/Users/jtakh/.claude/new-app.ps1 <name> -NoLaunch
```

`-NoLaunch` is required here and is not optional. The script's last step is to
start Claude in the new folder — correct when a human runs it from a terminal,
wrong from inside this session, where it would nest Claude inside Claude.

Pass `-Public` through only if the human explicitly asked for a public repo.

The script exits non-zero on any failure. It stops at the first failure and
reports which stages completed. If it fails, report the `FAILED:` line and the
`Completed:` list as-is rather than trying to continue by hand — that list is
how you know whether a GitHub repo now exists.

Step 0 preflights everything that can be checked before anything is created:
the name locally and on GitHub, the dev root, `gh` and `git`, that the template
repo is reachable, and that the interpreter the hooks invoke actually resolves.
Only then does it create the repo from the template, wire `core.hooksPath`, and
verify the `100755` bit on `.githooks/pre-commit` — the template commits the
hook executable, so the scaffold only checks that this clone still has it, and
fails if it does not. It patches `settings.json` to `py` if that is the
interpreter that exists.

**The script makes no commits, and it does not write the mode bit.** Only a
`settings.json` patch is ever left staged. Tell the human to review with
`git status` and commit it.

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
