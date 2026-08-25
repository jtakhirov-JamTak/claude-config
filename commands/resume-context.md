---
name: resume-context
description: Restore working context after /clear by reading session-context.md and verifying every claim in it is still true. Use at the start of a session. NOT writing that file (use /save-context); NOT durable preferences or decisions (those live in memory).
---

Restore working context after `/clear`. The source of truth is `session-context.md` at
the project root.

This complements the memory system, it does not replace it. Memory has already loaded
automatically. This command is for "what was I doing in this repo _right before_ /clear".

## Step 1 — Find the file

Look for `session-context.md` at the project root. If it is not there:

```
No session-context.md at the project root.
Run /save-context before /clear next time, or describe what you'd like to work on now.
```

Stop.

## Step 2 — Read it and flag staleness

The file has six sections: `Current goal`, `Verified state`, `Done this session`,
`Files changed`, `Unresolved risk`, `Exact next action`.

If `Updated:` is more than 7 days old, say so before anything else — the next action
almost certainly references code that has moved.

## Step 3 — Verify before acting

This is the step that earns this file its place. A restored context that is quietly wrong
is worse than no context, because it stops the looking.

1. **Every path in "Files changed"** — confirm it still exists. Report any that do not.
2. **Every symbol, function, or line "Exact next action" names** — grep to confirm it is
   still where the file says. Report drift; do not silently adjust.
3. **Every claim in "Verified state"** — check whether it is still true, or say plainly
   that it was true at write time and has not been rechecked. Do not restate it as
   current fact. A claim written as "not verified" stays not verified; it does not become
   true by being read back.

Report the result as a short list — what held, what drifted, what is missing — before
proposing any work.

## Step 4 — Execute

If everything held, execute "Exact next action".

If anything drifted, propose an updated next action and wait for confirmation. Read
"Unresolved risk" first — a failed fix recorded there means attempt 3 must test a
genuinely different explanation, not a third variant of the same one.

## Step 5 — If the user describes a different task

Proceed with the new task, but read the file anyway as background. It often holds
in-flight state — open branches, pending migrations, env-var changes — that the new task
will collide with.

## Rules

1. **Verification comes before execution**, always. Never act on the claims in the file
   without checking them.
2. **Name what turned out to be wrong.** Drift found is the useful output; a silent clean
   pass on a check that could not fail is not.
3. **Do not fabricate a plan from a vague pointer.** If "Exact next action" is not
   actionable, say so and ask.

$ARGUMENTS
