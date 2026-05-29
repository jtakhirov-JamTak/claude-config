---
name: resume
description: Restore working context after /clear by reading session-context.md and verifying it's still current
---

Restore working context after `/clear`. The source of truth is `session-context.md` at the project root.

This complements the memory system, it doesn't replace it. Memory has already been loaded into context automatically. This command is for "what was I doing in this repo *right before* /clear".

## Step 1 — Find the file

Look for `session-context.md` at the project root.

If it doesn't exist:

```
No session-context.md at the project root.
Run /save-context before /clear next time, or describe what you'd like to work on now.
```

Stop.

## Step 2 — Parse and display

Parse the file by `## ` headings. Display every section, sorted most-recent-`Updated:` first.

For each section, show one-line summaries:

```
# Session Context Overview

## {category} — Updated YYYY-MM-DD HH:MM (N days ago)
Working on: [first sentence of "Working On"]
Last result: [first sentence of "Results", or omit if N/A]
Next step: [first sentence of "Next Step"]
Running jobs: [from "Running Jobs", or omit if None]
```

End with:

```
Which context should we pick up? (number, name, or describe a different task)
```

## Step 3 — Flag staleness

For each section whose `Updated:` is more than 7 days old, append `[STALE — N days old]` to the heading. The next step almost certainly references files that have changed since.

If the user picks a stale section, confirm before proceeding:

```
This was last updated N days ago. The "Next Step" may reference code that's since changed.
Want me to spot-check the listed files first, or proceed as-is?
```

## Step 4 — Load full context for the chosen section

When the user picks a category:

1. Read the **full section** for that category.
2. **Verify before acting.** For each file in "Files Touched":
   - Confirm the file still exists.
   - Skim its current state — note any changes since the section was written.
3. For each item in "Running Jobs", check whether the process is still alive (or whether the artefact it was producing landed).
4. If "Next Step" references a specific symbol/function/line, grep to confirm it's still where the section says it is. Surface any drift before proceeding.

## Step 5 — Begin executing

Once the section's claims are verified (or drift is acknowledged), execute "Next Step". If verification turned up significant drift, propose an updated Next Step before acting, and wait for the user to confirm.

## Step 6 — If the user describes a different task

Skip the section and proceed with the new task — but read the chosen-or-most-recent section anyway as background. It often contains in-flight state (open branches, pending migrations, env-var changes) that the new task will collide with.

## Rules

1. Always show every section, sorted by recency — don't auto-pick the newest.
2. Always flag staleness when present — don't act on a stale section without acknowledging it.
3. Always verify file-and-symbol references before acting — sessions go stale; the codebase moves.
4. If the next step looks vague ("continue X"), ask the user what specifically to do — don't fabricate a concrete plan from a vague pointer.

$ARGUMENTS
