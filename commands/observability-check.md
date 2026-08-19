---
name: observability-check
description: Audit operational observability, stage-aware — do critical paths emit structured logs/events, is the error sink covered + cooldown-latched, are there alerts on money/auth/AI-spend/DB paths (metrics/traces/SLOs at scaling stage). Owns "will we get signal when this breaks?" Use before/after a launch or when adding a critical path. NOT whether logs leak PII (use /privacy-audit — it owns "logs don't leak"); NOT per-diff scrub correctness (use /review-changes).
---

Audit whether the system can tell you when it's broken. Output is a gap list ranked by blast-radius-when-blind, not a fix. Scope: $ARGUMENTS

## Reviewer conventions (apply to this skill)

- **Scope**: `$ARGUMENTS` may name a route / path / dir, or `stage=prelaunch|scaling` to set the bar; default scope is the whole repo's critical paths.
- **Exceptions**: read `.claude/exceptions.md` at repo root before reporting; skip matching entries; surface any suppressed must-have at the end.
- **Caps**: honor `top=N`, `critical-only`, `high-only`, `unbounded`. Default: list every must-have; cap should-have at 5.
- **Long-form rules**: `~/.claude/REVIEWER_CONVENTIONS.md`.

## Set the bar — stage-aware, anti-over-engineering

Establish the stage first (ask if unclear). The right floor differs, and a full APM build on a pre-launch solo app is over-engineering the staff-reviewer would reject:

- **Pre-launch / first users**: structured logs on critical paths, an error sink that actually captures, and 2–4 alerts on the paths that cost money or lock users out. That's it. Do **not** recommend tracing/SLO/dashboards here.
- **Scaling / paid traffic**: add metrics (rate/error/duration on hot endpoints), distributed traces across the AI/DB hops, dashboards, and SLOs with error budgets.

State the stage you judged against. The boundary with `/privacy-audit`: this skill checks logs **exist and are structured**; privacy-audit checks they **don't leak PII**. If you find a log line dumping journal text, note it as a privacy handoff — don't audit the scrub here.

## What to check

### Critical-path instrumentation

- Identify the paths that page you: auth, payment/entitlement webhook, AI-spend endpoints, DB writes on derived data. Each should emit a structured event (level, event name, correlation id, user id — never user content) on both success and failure.
- Failures are distinguishable: a `{ data, error }` branch that returns silently (§6 DB-ERROR-CHECK) is invisible to ops as well as to the user. Cross-reference — an uninspected `.error` is both a correctness bug and an observability hole.

### Error sink

Apply **ERROR-SINK-SCRUB** (`~/.claude/REVIEWER_CONVENTIONS.md` §6) — the scrubbing surfaces and the cooldown rule are maintained there; don't restate them.

- Configured and receiving (DSN/endpoint set in the deploy target).
- Severity/tagging lets you find the kind — a tag per failure mode, not one undifferentiated stream.
- The three leak surfaces are actually covered, not just `beforeSend` on the exception: breadcrumbs filtered at capture time, transactions scrubbed via their own hook or sampling held at zero.

### Alerting

- An alert exists for: auth failure spike, payment/entitlement write failure, AI-spend anomaly (cost runaway), DB error rate, and the error-sink-is-silent case (no events ≠ healthy; could be a broken sink).
- Alert routes somewhere a human sees within the window that matters. Note alert-fatigue risk: too many low-signal alerts and the real one gets muted.

### Scaling stage only

- Metrics on hot paths (RED: rate/errors/duration). Traces spanning the slow multi-hop calls. A dashboard for the critical user journey. SLOs with an error budget that someone owns.

## Output

For each gap: `path / area — what you'd be blind to — stage it's required at — suggested instrumentation`.

Priority:

- `must have` (for the stated stage) — a critical path with no signal on failure; an uncooldowned per-request capture; no alert on money/auth failure.
- `should have` — partial instrumentation; missing tag granularity; no silent-sink alert.
- `later` — scaling-stage items when pre-launch.

End with: counts by priority, the stage judged against, the single highest-leverage instrumentation to add, and a verdict — `we'd know at 2am` / `partial blind spots (n must-have)` / `flying blind (n must-have on money/auth)`.

$ARGUMENTS
