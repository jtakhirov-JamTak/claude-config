---
name: test
description: Author or audit tests with risk-based judgment — pick what deserves a test by observable failure mode, write to the project's conventions, or surface undertested high-risk surfaces (auth, money, derived data, migrations, regressions). Modes — write | audit. NOT running the suite (use the project's verify script); NOT diagnosing a failing test's bug (use /fix-bug); NOT coverage-% chasing.
---

Author or audit tests. Mode and target: $ARGUMENTS

Default mode is `write` if given a module/diff/symbol; `audit` if asked "where are we undertested" or given a wide scope. State which mode you're in.

## Reviewer conventions (`audit` mode only — `write` mode produces code, not a ranked report)

- **Scope**: `$ARGUMENTS` may name a module / dir / glob / symbol; default `audit` scope is the whole repo's risk surfaces.
- **Exceptions**: read `.claude/exceptions.md` at repo root before reporting; skip matching entries; surface any suppressed gap at the end.
- **Caps**: honor `top=N`, `critical-only`, `high-only`, `unbounded` in `$ARGUMENTS`. Default: list every uncovered money/auth surface individually; cap the rest at 10.
- **Long-form rules**: `~/.claude/REVIEWER_CONVENTIONS.md`.

## Discover first

Find the test runner and conventions before writing a line — read `package.json` scripts and **one nearby existing test end-to-end. That's your template.** Match its framework (vitest/jest/playwright), its file location (`__tests__/`, `*.test.ts`, co-located), its assertion style, its mocking/fixture approach, and how it sets up auth/DB state. A test that doesn't match the house pattern is friction, not coverage.

## The judgment (both modes) — risk before coverage

Test what has an **observable failure mode you can name**. Rank by blast radius:

1. **Money / entitlement** — anything that grants access, charges, or flips subscription state.
2. **Auth / authorization** — user-id filtering, gate helpers, cross-user isolation.
3. **Derived/persisted correctness** — raw+derived writes, version-stamped snapshots, idempotency.
4. **Migrations & data shape** — constraints, backfills, `null` vs `""`.
5. **Regression locks** — the exact input that just broke in a `/fix-bug`.

Do **not** test: framework behaviour, getters with no logic, code with no failure mode you can articulate (per the staff-reviewer calibration rule — a test for unbreakable code is noise). Don't chase a coverage percentage; chase the paths whose failure is silent and expensive.

- **Expected values must not be read off the implementation** — apply **SELF-ANCHORED-CHECK** (`~/.claude/REVIEWER_CONVENTIONS.md` §6). A test whose assertions were derived from what the code currently returns pins the bug in place and can only ever go green; anchor them to the spec, the ticket, or a hand-computed result instead.
- **A green test that never ran is worse than a missing one** — apply **VACUOUS-PASS** (`~/.claude/REVIEWER_CONVENTIONS.md` §6). In `audit` mode, a suite that exits 0 having discovered zero files, or an assertion fed a sentinel instead of a measurement, is a **HIGH** gap and not coverage. In `write` mode, give the runner a guard that fails when it finds nothing to run.

## Mode: `write`

1. State, in one line each, the failure modes worth a test for this target (from the ranking above).
2. For each: arrange (realistic fixtures, the project's auth/DB setup helper), act, assert the _behaviour_ — not the implementation detail that will churn.
3. Cover the boundaries `/grill` would attack: empty/whitespace, at-limit, null vs `""`, double-submit/replay, the `{ data, error }` error branch, the gated-403 path.
4. Match the sibling's structure exactly. Run the new tests; they must pass (or fail for the right reason if writing a red regression test first).

## Mode: `audit`

- Enumerate the risk surfaces above that exist in the repo.
- For each, grep for an existing test. Report covered / partial / **uncovered**.
- Rank uncovered by blast radius, not by file. A 90%-line-coverage repo with the entitlement webhook untested is more dangerous than a 40% repo with money fully covered — say so.

## Output

- `write`: the test files/blocks, the failure modes each one locks, and a one-line "what was deliberately not tested and why".
- `audit`: a risk-ranked gap table (surface / covered? / blast radius / one-line "what breaks silently if untested"), then the single highest-leverage test to write first.

Do not run the full suite as the deliverable — that's the project's verification gate (**VERIFY-GATE**, `~/.claude/REVIEWER_CONVENTIONS.md` §6). This skill's job is the tests' _existence and aim_, not their green checkmark.
