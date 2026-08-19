---
name: dep-audit
description: Audit dependencies for supply-chain / maintenance risk — vulnerabilities, outdated majors, lockfile integrity, license, and provenance/typosquat on newly-added packages. Use periodically, before a launch, or to vet adding a package. NOT unused-dep dead weight (use /techdebt); NOT app-code security like auth/injection (use /check-access or the built-in /security-review).
---

Audit dependencies for supply-chain and maintenance risk. Output is a risk-ranked report, not an automatic upgrade. Scope: $ARGUMENTS

## Reviewer conventions (apply to this skill)

- **Scope**: `$ARGUMENTS` may name a specific package to vet ("is X safe to add"), or be empty for a full dependency sweep.
- **Exceptions**: read `.claude/exceptions.md` at repo root before reporting; skip matching entries; surface any suppressed CRITICAL at the end.
- **Caps**: honor `top=N`, `critical-only`, `high-only`, `unbounded`. Default: list every CRITICAL + HIGH; cap MEDIUM at 10.
- **Long-form rules**: `~/.claude/REVIEWER_CONVENTIONS.md`.

## Discover first

Identify the package manager and lockfile (`package-lock.json`, `pnpm-lock.yaml`, `bun.lockb`, `yarn.lock`) — the audit command and lockfile-integrity check differ per manager. Read `package.json` for declared ranges. Note the runtime (Node version) so you can flag engines mismatches.

## Vulnerabilities

- Run the manager's audit (`npm audit --omit=dev` for prod surface, then full). Report by severity with the advisory id and the path that pulls the vulnerable transitive dep.
- For each CRITICAL/HIGH: is a fixed version available within the current major (safe bump) or does it need a breaking major (plan it)? Don't auto-run `audit fix --force` — it silently jumps majors.
- Distinguish **reachable** from **theoretical**: a vuln in a dev-only tool or an unused code path is lower priority than one in a request-handling path. Say which.

## Outdated & maintenance

- Outdated majors behind the current range — flag the ones with breaking changes that block a future upgrade if deferred too long.
- Unmaintained / deprecated packages (no release in a long time, archived repo, deprecation notice on install). A single-maintainer dep on a critical path is a bus-factor risk worth naming.

## Lockfile & integrity

- Lockfile present and committed; `package.json` ranges and the lockfile agree (a drifted lockfile means installs aren't reproducible).
- No integrity-hash mismatches. CI/install should use the frozen-lockfile flag (`npm ci`, `pnpm i --frozen-lockfile`).

## License

- Flag any copyleft (GPL/AGPL) or non-OSI license that conflicts with a commercial closed-source product. A surprise AGPL transitive dep is a legal finding, not a nit.

## New-dependency provenance (when vetting a specific add)

Before adding a package, sanity-check it's not a supply-chain trap:

- **Typosquat**: name is a near-miss of a popular package; check you mean the real one.
- **Provenance**: download counts, repo linked and matches, recent releases, more than one maintainer or a known org.
- **Footprint**: does it pull a large transitive tree or run install scripts? A one-function need doesn't justify a 40-dep subtree.
- **Alternative**: is it already solvable with a dep you have, or a few lines of first-party code? (Ties to the staff-reviewer "three lines, not a framework" rule.)

## Output

Risk-ranked, `package@version — risk type — severity — reachable? — suggested action (bump within major / plan major / replace / accept)`:

- `CRITICAL` — known-exploited vuln on a reachable path; AGPL on a commercial product; confirmed typosquat.
- `HIGH` — high-severity vuln reachable; unmaintained dep on a critical path; lockfile not reproducible.
- `MEDIUM` — outdated major with breaking changes pending; dev-only vuln; large-footprint dep for a small need.
- `LOW` — cosmetic version lag, advisory on an unreachable path.

End with: counts by severity, scope, the single highest-leverage action, and a verdict — `SUPPLY CHAIN OK` / `ATTENTION (n HIGH)` / `STOP (n CRITICAL — reachable vuln / license / typosquat)`. For a single-package vet, end with `SAFE TO ADD` / `ADD WITH CAVEAT` / `DON'T ADD` + one-line reason.

$ARGUMENTS
