---
name: explain
description: Explain what a file, function, or concept does in plain non-technical English — analogies, no jargon, read from the actual code rather than inferred. Use when you want to UNDERSTAND something that already exists. NOT a correctness review (use /review-changes); NOT a summary of what recently changed (use /diff-summary); NOT diagnosing a specific broken thing (use /fix-bug).
---

Explain the thing named in `$ARGUMENTS` — a file path, a function or symbol name, a folder, a config key, or a plain-language question ("how does login work here?") — to someone who does not read code.

## Read it first, always

**Never explain from a name.** A file called `storage.ts` may not handle storage; a function called `validateUser` may not validate anything. Open the file. Follow what it actually calls. If the explanation depends on something you have not opened, open that too.

Trace **one real path end to end** rather than paraphrasing what things are named. "The button calls `saveEntry`, which writes to the `entries` table" is worth more than three sentences about responsibilities.

## Mark what you are unsure about

An explanation that sounds confident and is wrong is worse than no explanation — the user cannot tell the difference and will build on it.

- State only what you read. If you are inferring, say **"I think"** in that sentence.
- If something is genuinely unclear from the code, say **"I could not tell from the code"** and name what you would need to check (run it, query the DB, read a config not in the repo).
- Never smooth over a gap to make the explanation flow.

## How to write it

- Talk to someone smart who does not code. Short sentences. Common words.
- No jargon. If a technical term is unavoidable, define it in parentheses the first time.
- One everyday analogy where it genuinely helps — a librarian, a receptionist, a filing cabinet. Skip it if it would strain.
- 3–6 sentences by default. Expand only if asked, or if the thing is genuinely large.
- Say **when** it runs and **what calls it** — that is usually the missing piece, not the logic.

## Structure

1. **What it is** — one sentence. Files: "This file handles…". Functions: "This does…".
2. **When it runs** — what triggers it.
3. **Why it matters** — what would break or go wrong without it.
4. **Anything worrying** — a bug, a risk, a data-loss path, a secret in the wrong place. Say it plainly, in the same simple language. Do not save it for a review; the user may never run one.

## Example

> **`server/storage.ts`**
>
> This file is the librarian for your database. Every time the app saves a journal entry, looks up a habit, or checks whether someone has paid, the request goes through here. No other file talks to the database directly — which is good, because it means there is one place to look when data behaves strangely.
>
> It holds about 100 operations, grouped by feature (journals, habits, tasks).
>
> ⚠️ One thing worth knowing: about a dozen of these operations do not check whether the database returned an error. If one of those fails, the app shows an empty screen instead of a warning — so it looks like your data vanished when it is actually still there.
