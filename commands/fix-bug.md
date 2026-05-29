---
name: fix-bug
description: Structured bug fix — reproduce, locate, diagnose, fix, verify — with rabbit-hole prevention after 3 attempts
---

Fix a specific bug. Stay focused on the smallest change that resolves the reported behaviour. Bug description: $ARGUMENTS

## Before starting

- Search the codebase / commit history for the same symptom — there may already be a fix or an attempt. Don't repeat a failed approach.
- Read any project notes (CLAUDE.md, README, docs) for relevant rules near the area of the bug.

## Process

### 1. Reproduce
- State the observed behaviour vs the expected behaviour in one sentence each.
- Identify the minimum input or sequence that triggers it. If you can't reproduce, stop and ask the user for the steps — don't guess.

### 2. Locate
- Find the code that runs in the failing path. Check both client and server if the symptom could originate on either side.
- Read the surrounding context — bugs rarely live alone, but resist the urge to fix neighbours in the same diff.

### 3. Diagnose
- State the root cause in plain English, in one sentence.
- Distinguish symptom from cause: "the button doesn't fire" is a symptom; "the parent re-renders and replaces the handler ref before the click registers" is a cause.
- If the cause is in a different layer than the symptom (UI symptom from a server-side cause, or vice versa), say so explicitly before changing code.

### 4. Fix
- Make the smallest change that addresses the cause. Don't refactor neighbours, don't tidy unrelated code, don't add error handling for cases that can't happen.
- If the fix requires changes in two places, that's fine — but state both up front, don't drift mid-edit.
- Preserve the existing pattern. If the project does X via helper Y everywhere, fix this site to use Y, not a hand-rolled equivalent.

### 5. Verify
- Run the project's type check.
- Re-run the original reproduction — confirm the failing behaviour is gone.
- Skim the surrounding tests; if a test covering this path exists, run it. If no test covers it, lock the regression: run `/test write` on the failing path so the exact input that broke can't silently break again (the highest-value test there is — a confirmed real failure mode).

## Rabbit-hole prevention

- **Attempt 1** — the most obvious fix from the diagnosis.
- **Attempt 2** — if attempt 1 didn't resolve it, *re-diagnose first*. Don't try a second fix to the same theory; revisit whether the theory was right.
- **Attempt 3** — if still broken after a re-diagnosis, **STOP**.

On STOP, tell the user:
1. The three attempts in order, one line each.
2. What you now think the real cause might be (different from the original theory if appropriate).
3. Whether this needs a different approach entirely — a different layer, a different abstraction, asking someone with context the codebase can't provide.

Do not silently start attempt 4. Surface the stuck state so the user can redirect.

## On success

- Surface the lesson explicitly: was this a pattern that could recur elsewhere? If yes, suggest a one-line addition to project notes (CLAUDE.md, playbook) so the next session doesn't repeat it.
- Don't add a comment in the code explaining the fix — the commit message is where that lives.
