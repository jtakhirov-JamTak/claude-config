---
name: perf-check
description: Audit performance and scaling risk on existing/running code — data layer (N+1, unbounded reads, missing indexes, query plans) and client bundle (weight, code-splitting). Use when something's slow, before a traffic increase, or to pressure-test a data model at 10×. NOT a functional bug whose symptom isn't latency (use /fix-bug); NOT a design not yet built (ask for an architecture critique); NOT mobile touch/viewport (use /mobile-check).
---

Audit performance and scaling risk on code that already exists. Output is a severity-ranked report, not a fix. Scope: $ARGUMENTS

## Reviewer conventions (apply to this skill)

- **Scope**: `$ARGUMENTS` may name a route / page / dir / glob, or `surface=data|bundle` to limit which half runs; default scope is the whole repo's hot paths.
- **Exceptions**: read `.claude/exceptions.md` at repo root before reporting; skip matching entries; surface any suppressed HIGH at the end.
- **Caps**: honor `top=N`, `critical-only`, `high-only`, `unbounded`. Default: at most 5 LOW + 10 MEDIUM listed individually, rest summarized.
- **Long-form rules**: `~/.claude/REVIEWER_CONVENTIONS.md`.

## Discover first

Identify, before judging: the ORM / query API (Drizzle, Prisma, supabase-js/PostgREST, raw SQL), the bundler (Vite, Next, webpack) and whether a bundle analyzer exists, the rendering model (SSR/CSR/RSC), and where the hot paths are (the routes/pages a user hits most). Don't assume — a `db.query` pattern differs from a PostgREST `.select()` differs from raw SQL.

## Data layer — the queries that crawl at 10×

- **N+1**: a query inside a loop / `.map` / per-row fetch. The classic 10×-rows-10×-queries trap. Look for awaited DB calls inside iteration.
- **Unbounded reads**: `.select()` / `findMany` with no `limit`. Works at 10 rows, dies at 10K. Every user-scoped list needs a cap or pagination.
- **Missing indexes**: any column used in `WHERE`, `ORDER BY`, or a join that has no index. Cross-check the migration/schema. `(user_id, created_at DESC)` is the common one.
- **Over-fetching**: `SELECT *` / full-row reads when the consumer uses three columns; large `jsonb` blobs pulled to render a count.
- **Query plan**: for the slowest 1–2 queries, recommend `EXPLAIN ANALYZE` (or the ORM's logging) — don't guess seq-scan vs index-scan, measure it.
- **Sync waterfalls**: independent awaited queries that should be `Promise.all`'d (but mind the per-row `.error` inspection — see §6 DB-ERROR-CHECK).

## Client bundle — what ships to the phone

- **Bundle weight**: total JS shipped on first load; flag the largest contributors. Recommend the analyzer (`vite-bundle-visualizer`, `@next/bundle-analyzer`) rather than eyeballing.
- **No code-splitting**: heavy routes/components not lazy-loaded; a charting/editor lib pulled into the initial chunk.
- **Heavy deps**: a multi-hundred-KB library used for one helper (moment, lodash-whole, an icon set imported wholesale).
- **Images**: not using the framework's image primitive or missing width/height — layout shift + oversized payloads on mobile data.
- **Render-blocking**: synchronous third-party scripts, fonts without `display: swap`.

## Output

Severity-ranked, `file:line — finding — what it costs at 10× — suggested direction`:

- `CRITICAL` — unbounded query on a growing table in a hot path; N+1 that multiplies with users.
- `HIGH` — missing index on a filtered hot-path column; a heavy lib in the initial bundle on a mobile-first app.
- `MEDIUM` — over-fetching; missing code-split on a non-critical route; image not optimized.
- `LOW` — micro-inefficiency with no measurable impact at current scale.

End with: counts by severity, scope, the single highest-leverage fix, and a verdict — `NO SCALING BLOCKERS` / `WATCH (n HIGH)` / `WILL NOT SCALE (n CRITICAL)`. State the scale assumption you judged against (e.g. "at 10K rows/user, 1K concurrent").

$ARGUMENTS
