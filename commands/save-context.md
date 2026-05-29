---
name: save-context
description: Save session context to a project-local file before /clear, with archiving and category detection
---

Save the current session state to a project-local file so the next session (after `/clear`) can resume.

This is the **handoff** layer of persistence. It is *not* the memory layer.
- **Memory** (`~/.claude/projects/.../memory/`) is for things that should outlive any single project session — user preferences, project decisions with lasting context, durable references. It's reloaded automatically.
- **`session-context.md`** is for "what's in flight right now in this repo". It's stale within days. It lives in the project root and is read by `/resume`.

If something belongs in memory (a decision, a preference, a rule), save it via the memory system instead. Don't duplicate it into session context.

## Step 0 — First-run setup (only if `session-context.md` doesn't exist)

Ask the user once:

```
Setting up session context for this repo. What areas do you work on here?
(e.g. frontend, backend, api, devops, design) — or say "auto" and I'll infer from the directory structure.
```

Create the file with:

```markdown
# Session Context
<!-- categories: frontend, backend, api -->
```

## Step 1 — Archive the current file

Before any write, snapshot the existing file. This machine's default shell is PowerShell (no `mkdir -p`, no `cp`, no `$(date …)` substitution) — use the PowerShell form, or run the Bash form via the Bash tool:

PowerShell:
```
New-Item -ItemType Directory -Force .archive | Out-Null
$ts = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
Copy-Item session-context.md ".archive/session-context-$ts.md"
```

Bash:
```
mkdir -p .archive && cp session-context.md ".archive/session-context-$(date -u +%Y%m%dT%H%M%SZ).md"
```

Also prune the archive: keep the 20 most recent snapshots, delete the rest. Otherwise `.archive/` grows forever and clutters file searches.

## Step 2 — Detect the active categories

Scan this conversation for category mentions — file paths touched, topics discussed, tools invoked. Match against the `<!-- categories: ... -->` list. If a new category emerges that fits, add it to the list. If no category fits, use `general`.

## Step 3 — Update only the detected sections

Read the existing file, split on `## ` headings.

For each detected category:
- If a section already exists with that name, **replace** it.
- If not, **append** a new section.

Leave every other section exactly as it was. Do not "tidy" sections you didn't touch this session — staleness is data, and pruning belongs in Step 6.

## Step 4 — Section format

```markdown
## {category}
Updated: YYYY-MM-DD HH:MM (UTC)

### Working On
[1–3 sentences describing the current task and its goal.]

### Key Decisions
- [Decision, with one-line reasoning.]

### Results
[What was actually accomplished this session. Metrics, completed deliverables, before/after. "N/A" if it was purely setup/exploration.]

### Files Touched
- path/to/file — what changed
- path/to/file — what changed

### Running Jobs
[Background processes still running (builds, deploys, long agents), or "None".]

### Context
[References needed to resume that the codebase doesn't already encode — error messages, URLs, version pins, decisions reached out-of-band.]

### Next Step
[One specific action the next session should take first. Concrete enough to hand to another developer.]
```

## Step 5 — Rules

1. **Archive first, then write.** Never lose data.
2. **Only touch detected sections.** Other categories' sections stay byte-identical.
3. **Each section ≤ 50 lines.** If it's growing past that, the durable parts should move to memory; only the in-flight parts belong here.
4. **"Next Step" must be actionable.** "Continue X" is bad. "Re-run the failing test in X and fix the type error on line 42" is good.
5. **No marketing voice.** No "successfully completed". No "comprehensive".

## Step 6 — Prune stale sections (one-shot, ask the user)

After writing, check the file for sections whose `Updated:` timestamp is more than 14 days old. Surface them with one-line summaries and ask:

```
These sections haven't been updated in N days — keep or drop?
- frontend (Updated 2026-03-01): "Working on insights v2 rebuild — paused"
- billing (Updated 2026-02-12): "Stripe webhook investigation"
```

If the user picks "drop", remove the section. If "keep", leave it. Default to no action if the user doesn't respond — never delete silently.

## Step 7 — Confirm

```
Context saved for: <category1>, <category2>
Archive: .archive/session-context-<timestamp>.md
Ready for /clear
```

If anything was pruned, list what.

$ARGUMENTS
