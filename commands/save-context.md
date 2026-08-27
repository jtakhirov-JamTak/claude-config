---
name: save-context
description: Save session context to a project-local file before /clear. Writes six fixed sections and nothing else. Use before /clear. NOT restoring it afterwards (use /resume-context); NOT durable preferences or decisions (those go to memory, not session context).
---


Save the current session state to `session-context.md` at the project root so the next
session can pick it up.

This is the **handoff** layer of persistence. It is _not_ the memory layer.

- **Memory** (`~/.claude/projects/.../memory/`) is for things that should outlive any
  single session — preferences, durable decisions, references. It reloads automatically.
- **`session-context.md`** is "what is in flight right now in this repo". It is stale
  within days. It is read by `/resume-context`.

If something belongs in memory, save it there instead. Do not duplicate it into session
context.

## The file

The file describes the one active intent. Overwrite
it whole — there is no archive, no category detection, and no per-section merge. Six
sections, in this order, and nothing else:

```markdown
# Session Context

Updated: YYYY-MM-DD HH:MM (UTC)

## Current goal

[1–3 sentences: the one thing this session is for, and what "done" looks like.]

## Verified state

[What is known true because it was checked this session — a test that passed, a query
that returned, a log line. Name the check, not the impression. "Not verified" is a
legitimate entry and is more useful than a guess.]

## Done this session

[What actually landed. "N/A" if the session was purely exploration.]

## Files changed

- path/to/file — what changed
- path/to/file — what changed

## Unresolved risk

[What could still be wrong, what was assumed rather than checked, and any failed fix
attempts with the theory each one disproved. "None known" if that is true.]

## Exact next action

[One specific action, concrete enough to hand to someone else. "Continue X" is not an
action. "Re-run the failing test in src/foo.test.ts and fix the type error on line 42"
is.]
```

## Rules

1. **Overwrite the whole file.** The previous contents describe an intent that is over.
2. **Every path in "Files changed" must be real.** `/resume-context` verifies them; a
   fabricated path turns that check red for no reason.
3. **"Verified state" carries the evidence, not the conclusion.** If nothing was checked,
   say so — that is the entry that stops the next session trusting a guess.
4. **"Exact next action" must be actionable** without re-reading this conversation.
5. **No marketing voice.** No "successfully completed", no "comprehensive".

## Confirm

```
Context saved to session-context.md
Next action: <one line>
Ready for /clear
```

$ARGUMENTS
