# Make README.md a landing page, not a setup card

## Context

External review of the repository found three things. Assessed against the code:

1. **"The README does not explain the real value" — valid, and the biggest gap.** Today `README.md`
   is 55 lines: a one-line description, stack, prerequisites, setup, commands, two doc links. It
   never states what problem the template solves, what it guarantees, what it deliberately excludes,
   or that it was built from two shipped apps. (Slight overstatement in the review: line 5 *does*
   name the audience — "for security-sensitive applications" — but it is one clause, easy to miss.)
2. **"It is a heavy foundation" — a positioning fact, not a defect.** Every dependency is already
   justified individually in `ARCHITECTURE.md` → *Library justifications*, and playbook §7 gates new
   ones. Adopt the reviewer's label; change nothing about the stack.
3. **"Maintenance cost will be meaningful" — correct, and understated in one direction.** Each
   contract the reviewer lists already has a check that fails loudly (`check:analytics`,
   `check-generated-types`, `check:sw`, `check:bundle`, `verify:example-removal`), so drift is caught
   mechanically. The genuine residual risk is *upstream* churn, which no check covers.

**This is a surfacing problem, not a missing-content problem.** Everything the review asks for
already exists and is maintained elsewhere in the repo. The README's job is to index it, so the
fix adds no new source of truth to keep in sync.

Also fixing a gap the review missed: `CLAUDE.md` names five maintained documents; the README links
two (`ARCHITECTURE.md`, `START_NEW_APP.md`) and omits `CLAUDE.md` and
`.claude/ENGINEERING_PLAYBOOK.md`.

## Approach

Rewrite `README.md` as a short landing page (~100 lines, scannable). Keep `Template version:
v1.0.0` — `CLAUDE.md` refers to it. Setup and commands survive unchanged but move below the value
sections.

**Hard rule for execution: every claim must be traceable to an existing document, and verified
against it while writing — not recalled.** If a sentence cannot be sourced, cut it rather than
invent a guarantee the code does not make.

New sections, in order, each 2–4 lines plus a link to the doc that owns the detail:

- **Headline** — "Opinionated production foundation for mobile-first, security-sensitive
  Next.js/Supabase applications." Explicitly *not* a lightweight starter (review point 2).
- **Who this is for / not for** — for: apps where a cross-user data leak is the unacceptable
  failure. Not for: throwaway prototypes or content sites — scaffolding is a ~30-minute process
  (`START_NEW_APP.md`) and the gates assume you want them.
- **What it guarantees** — summarize the `CLAUDE.md` non-negotiables: RLS deny-by-default on every
  client-reachable table with a cross-user test, no secrets client-side, allowlisted typed analytics
  enforced in both TypeScript and the database, every DB change a committed migration, `npm run
  verify` green before push. Link `CLAUDE.md`.
- **What is deliberately excluded** — name the *Optional modules* list from `ARCHITECTURE.md` →
  Boundaries (error vendor, payments, AI, admin, file storage, push, persistent protected-data
  cache, offline mutation queue, anonymous analytics, virtualization) and that the example feature
  is one deletable folder verified by `npm run verify:example-removal`. Link `ARCHITECTURE.md`.
  This section does double duty: it is also the honest answer to "heavy".
- **Built from shipped applications** — the distinctive asset that is currently invisible:
  `ARCHITECTURE.md` → *Source provenance* classifies every foundation piece as copied as-is,
  copied with changes, or rebuilt cleanly, citing the two audited apps (`pure-eq`, `you-inc`); the
  *Foundation Fix Log* carries 15 dated entries, each a real defect with its generic fix and
  regression test. Link both.
- **Cost of adoption** — per the chosen option: the interacting contracts (analytics types + DB
  constraints, generated types, service-worker rules, performance budgets, pinned versions), that
  each has a check which fails loudly under `npm run verify`, and the one thing checks cannot catch
  — upstream churn. Cite the concrete instance already recorded in *Trade-offs*: Serwist currently
  requires Webpack, so builds run `--webpack`. **State no review cadence** — an undocumented-but-real
  policy is better than a documented one that is not held.
- **Documentation** — link all five maintained documents, not two.

## Files

- `README.md` — the only file changed.

Not touched: `ARCHITECTURE.md`, `CLAUDE.md`, `START_NEW_APP.md`, `.claude/ENGINEERING_PLAYBOOK.md`.
They are the source of truth; if a claim in the README is wrong, the fix is to correct the README to
match them, not to edit them to match the README.

## Verification

Content correctness matters more than tooling here, so check the claims first:

1. **Source every claim.** Re-read the *Boundaries*, *Library justifications*, *Trade-offs*, and
   *Source provenance* sections of `ARCHITECTURE.md` and the non-negotiables in `CLAUDE.md`, and
   confirm each README statement against them. Re-count the Fix Log rows rather than trusting the
   number above.
2. **Verify every command still exists** in `package.json` `scripts` before it appears in the
   README — including `verify:example-removal`, and any referenced from prose.
3. **Verify every link resolves**, including the relative path `.claude/ENGINEERING_PLAYBOOK.md`.

Then:

```bash
npm run format:check   # prettier scans .md at the repo root; a long line or stray table breaks it
npm run verify         # full gate, must be exit 0 before push
```

`test:e2e`, `db:reset`, and `db:test` are not required — this is a documentation-only change with no
code, migration, or RLS impact. Say so explicitly when reporting rather than leaving it implied.
