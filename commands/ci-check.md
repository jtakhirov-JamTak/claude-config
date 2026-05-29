---
name: ci-check
description: Set up or audit a lightweight CI pipeline (GitHub Actions etc.) running typecheck/lint/build on every push — earlier failure signal than the deploy-time build. Build/lint/typecheck gating now; test-gating deferred until a green suite exists (/test first). NOT running checks locally (use the verify-app agent); NOT the pre-deploy risk review (use /deploy-check); NOT diagnosing a broken build (use /fix-bug).
---

Set up or audit a lightweight CI pipeline. Target / provider: $ARGUMENTS

## The bar — earlier signal, not a heavy gate

This is deliberately thin. The job is to move the **typecheck / lint / build** signal earlier — from "Vercel fails the deploy" to "the push fails CI a minute sooner, with lint included." For a solo founder on commit-straight-to-main + auto-deploy, that's the whole marginal value: faster feedback and lint that the production build may skip. Don't over-build it.

**What this does NOT add (yet):** test-suite gating. There's no point gating on a suite that doesn't exist. The moment `/test` produces a green suite, come back and add the `test` job — that's the planned second pass, not a gap to apologize for. State this split explicitly in the output so the deferral is a recorded decision.

## Discover first

- The host/CI platform (GitHub Actions, GitLab CI, etc.) — check for an existing `.github/workflows/` or equivalent before creating one.
- The package manager + lockfile (drives the install step and the frozen-lockfile flag).
- The real script names (`package.json`): typecheck (`tsc --noEmit`), lint, build. Reuse the **same commands the verify-app agent discovers** — CI and local verification should run identical steps, not drift.
- Whether the deploy provider already runs a build (Vercel does) — so CI's build step is about *earlier* signal + lint, and you say that, rather than implying prod is unprotected.

## Audit mode (a workflow already exists)

- Does it run on the right trigger (push to main + PRs)?
- Does it install with a frozen lockfile (`npm ci` / `--frozen-lockfile`) so CI matches the lockfile?
- Does it run typecheck AND lint AND build — or is one silently missing?
- Is the Node version pinned to match the deploy target?
- Are secrets referenced correctly (not echoed into logs)?
- Is it fast enough to be useful (cache `node_modules` / the framework build cache)?

## Setup mode (no workflow yet)

Propose a minimal workflow that:
1. Triggers on push to the default branch + pull requests.
2. Checks out, sets up the pinned Node version, installs with the frozen-lockfile flag (cached).
3. Runs typecheck → lint → build, failing on any error. Mirror the verify-app step order.
4. Leaves a clearly-marked, commented-out `test` job stub with a one-line note: "uncomment once /test produces a green suite."

Show the YAML, explain each step in plain language (the founder is non-technical), and note that committing it doesn't change deploy behaviour — it adds a check, it doesn't block Vercel.

## Output

- Audit mode: gaps found (missing step / wrong trigger / no lockfile freeze / no cache), ranked, each with the one-line fix.
- Setup mode: the workflow file, a plain-language walkthrough, and the explicit "build/lint/typecheck now; test-gating deferred to a green suite" note.

End with a verdict: `CI COVERS THE FAST SIGNAL` / `GAPS (list)` / `NO CI — workflow proposed above`, plus the one deferred item (test-gating) and its unblock trigger.

$ARGUMENTS
