# Global Instructions

Applies to every project unless a project-level CLAUDE.md says otherwise.

## Environment

- Windows 11, PowerShell is the primary shell. Bash is available but takes POSIX syntax.
- PowerShell 5.1: no `&&`, no `||`, no ternary. Chain with `;` or `if ($?) { ... }`.
- Never work directly out of `C:\Users\jtakh` — it is the home directory, not a project.
  Start in the project folder so its CLAUDE.md loads and searches stay scoped.

- Node scripts that spawn a CLI: `spawnSync("supabase")` / `spawnSync("npm")` cannot
  launch Windows `.cmd` shims. Use `npx --no-install <cli>` with `shell: true` on win32,
  and always surface `result.error` — unchecked, the script exits 0 and the gate reports
  success without having run. This one recurred four times in eight days before it was
  written down; see `VACUOUS-PASS` in `REVIEWER_CONVENTIONS.md` §6.
- Every repo needs `.gitattributes` containing `* text=auto eol=lf`. Git for Windows
  ships `core.autocrlf=true`, so without it a fresh clone materialises every file as
  CRLF and `format:check` fails on all of them before a line is edited.
- Gitignore Claude Code's own local state at a repo root — `session-context.md`,
  `.claude/settings.local.json`, tool report artifacts. Prettier and lint scan the
  repo root, so untracked local state fails `format:check`.

## Working style

- Do not make things up. Do not provide an answer until you can verify it in the code.
- Lead with the answer. Keep explanations short; expand only when asked.
- Two failed fixes mean the diagnosis is wrong, not the fix. Attempt 3 must test a
  genuinely different explanation — never a third variation on the same theory — or
  stop. On stopping, record per attempt: the theory, the evidence that disproved it,
  and the remaining unknown — as a dated entry in the project's fix log with the fix
  field left open. A protocol that says "record it" without naming a file never runs.
  The disproved theories are the most valuable part: an unrecorded dead end gets walked
  again. Say which layer you believe the cause is in before editing code.
- One intent per session. "While I'm here" is how rabbit holes start. Never leave a
  session mid-broken — end at a green verify or an explicit stash.
- Flag security and data-loss risks proactively, even when unasked — assume I will
  not spot them myself.
- Before deleting or overwriting anything, show me what it is first.

## Verification

- Never state something as fact because I said it, because a note or doc said it,
  or because it sounds right. Check the code. Run the query. Read the file.
- For anything about data: query the live database. Do not infer schema or state
  from migrations, type files, or an earlier conversation. A migration shows what
  was intended. The database shows what is true.
- If you cannot verify something, say "I have not verified this" in that sentence.
  Never present it as fact and correct it later.
- This applies to my own notes and pasted research. Treat them as claims to test,
  not as facts to repeat.

## Code

- Match the conventions already in the file. Don't introduce a new pattern for a
  problem the codebase has already solved somewhere else.
- Don't add comments explaining what the code plainly does.
- Never commit or push unless I ask.
- Secrets belong in `.env` files only, never in source, logs, or committed docs.
- Never delete data with history value — archive it (`archived_at`). Preserve user
  input when a request fails. Only a user's explicit delete removes a row.
- UTC in the database, always. Convert at the edge.

## Recording what breaks

- Every project keeps a fix log: one dated entry per real defect — problem · fix ·
  regression test · where it was found. A confirmed failure is the highest-value test
  that exists, so lock every fixed bug with a regression test on the exact failing input.
- A template-derived app keeps two logs: `docs/FIX_LOG.md` for defects inherited from the
  template, `docs/APP_FIX_LOG.md` for its own. Sort each by asking "would the next app
  built from this template hit it?" — yes goes to the template's log, no stays local. A
  project with no template keeps one log, its own.
- Any app holding real user data keeps a restore runbook: how to dump, how to restore
  into a fresh project, how to verify the restore actually worked, and the date it was
  last drilled. A backup that has never been restored is a hope, not a backup. Drill it
  before launch and after any change to the backup path.
- Decisions get the same treatment (`docs/DECISIONS.md`), kept verbatim with the numbers
  that settled them. Read it before re-attempting anything recorded as rejected — the
  experiment has already been run, and a rejected optimisation is only useful if the
  evidence against it survives.

## Active projects

Inventory, state, and repo list: `~/.claude/PROJECTS.md` — read it before judging risk
in an unfamiliar repo. The one fact that changes behaviour everywhere and so stays here:
**`pure-eq` is the only app with real users**, so "is this safe to ship" means something
different there than in the other four.

## This directory is versioned

`~/.claude` is itself a git repo (branch `master`) holding the authored skill set.
The `.gitignore` denies everything at the root and re-includes only the authored
files, so runtime state, transcripts, and `.credentials.json` can never be tracked.
After changing a command, an agent, `REVIEWER_CONVENTIONS.md`, or this file, commit
it — an uncommitted skill set is the one thing here with no backup.

## Custom commands

`~/.claude/commands` holds an authored review and scaffolding set (`/review-changes`,
`/full-review`, `/grill`, `/deploy-check`, `/add-*`, etc.). Prefer these over generic
equivalents — they encode project-specific conventions. Shared review conventions and
the rules for maintaining the set: `~/.claude/REVIEWER_CONVENTIONS.md`.

When I ask in normal words for something one of these commands covers, read that
command file and follow it. Don't improvise your own version. Typing `/commit` and
saying "commit and push" must behave identically.
