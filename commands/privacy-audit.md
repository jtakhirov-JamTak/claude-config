---
name: privacy-audit
description: Inventory personal-data flows and gaps in privacy policy, deletion, and export — PII columns, sub-processors, deletion cascade, data-rights. Use when auditing how the app handles personal data. NOT a code-security/access pass (use /check-access or the built-in /security-review).
---

Audit the project's handling of personal data. Output is an inventory + gap list, not legal advice.

## Reviewer conventions (apply to this skill)

- **Scope**: `$ARGUMENTS` may name a table, route, dir, or glob to narrow the audit; default scope is the whole repo.
- **Exceptions**: read `.claude/exceptions.md` at repo root before reporting; skip matching entries; surface any suppressed must-have at the end.
- **Caps**: honor `top=N`, `critical-only` (must-have-before-launch only), `high-only` (must-have + required-for-regulated-cohort), `unbounded` in `$ARGUMENTS`. Default: list every must-have and required individually; cap should-have at 5 and summarize the rest.
- **Long-form rules**: `~/.claude/REVIEWER_CONVENTIONS.md`.

## Step 0 — Discover

Before mapping data flows, identify:

- DB(s) and their managed-encryption posture (most managed Postgres / Mongo / RDS encrypt at rest by default — confirm rather than assume)
- Auth provider (managed services handle password hashing themselves; do not grep for `bcrypt` if you're not running your own auth)
- AI / transcription / payment / analytics providers in use, and what user data is sent to each
- The framework so you know where forms, routes, and analytics tags live (Next.js App Router, SvelteKit, Rails, etc.)

Don't carry forward assumptions from other projects (Replit, raw SPA, hand-rolled auth) — verify each.

## What to inventory

### 1. Data collected

Walk the DB schema (or ORM models). For every column that contains user-provided or user-derived data, classify:

- **Identifiers** — email, phone, name, IP, device id.
- **Sensitive content** — journals, messages, emotional/health/financial data, voice recordings, photos.
- **Behavioural** — usage logs, AI prompt history, audit events.
- **Derived** — embeddings, AI summaries, scores. These often inherit the sensitivity of their source.

For each: where it's stored, who can read it (RLS / policies), retention default.

### 2. Data sharing

For every external provider the app calls server-side or client-side:

- What user data goes out (verbatim user text? hashed identifiers? metadata only?)
- Under what circumstances (every request? on opt-in?)
- Whether the provider's terms permit using customer data to train their models (toggle status if applicable — many providers default to training-on by default and require explicit opt-out)
- Whether the provider is named in the privacy policy as a sub-processor

Client-side: every analytics tag, error sink, and third-party widget. Each is a separate sub-processor.

### 3. User rights surface

- **Access** — can a user view all data the system holds about them?
- **Export** — endpoint that returns everything in a portable format. If it exists, verify it walks every user-scoped table (not just the obvious ones — derived snapshots and observation tables are commonly missed).
- **Correction** — can a user edit identifiers and content?
- **Deletion** — endpoint that cascades through every user-scoped table. Each user-scoped table should have `ON DELETE CASCADE` back to the auth user, OR the deletion endpoint walks them explicitly; a table without a cascade and not in the walk is a deletion gap. **Verify against the LIVE DB, not just migration/type files** — those drift (a table added without a cascade, or a migration not yet applied, won't show in the files but will in the database). If a DB is reachable, run the `pg_constraint` cascade query from `/db-check` (do NOT use `information_schema` — it hides `auth.users` FKs from the query role and returns a false empty). Reading schema files is the fallback when there's no DB access; say which you used, and never claim "cascade verified" from files alone.
- **Portability** — same as export but specifically in a structured, machine-readable format.

### 4. Security measures (state for the policy)

- Encryption in transit (HTTPS only; HSTS configured if available)
- Encryption at rest (state which provider provides it)
- Password handling (managed provider name + their published posture, OR if self-hosted, the hash function used)
- Session security (cookie flags: `Secure`, `HttpOnly`, `SameSite`)
- Logging — confirm sensitive content is never logged (cross-reference with the error-sink scrub config)

### 5. Retention

- Default retention for each table — none, N days, indefinite?
- Backup retention via the DB provider
- Deletion of soft-deleted rows (if soft delete is used, when do they hard-delete?)

## Gap list

For each category, classify:

- **Must have before any real users** — privacy policy, terms, deletion, breach plan.
- **Required if targeting EU / UK / California / Brazil** — DSR fulfilment workflow, lawful-basis statement, sub-processor list, data-residency commitments.
- **Should have** — retention policy document, accessibility statement, security disclosures page.

For each gap: severity, the specific data class or right that's exposed, and a one-line "what would need to be true to close this".

## Output

1. Data inventory table (column / classification / table / retention / provider exposure)
2. Provider sub-processor list (provider / data sent / training opt-out status)
3. User-rights gap list
4. Prioritized "build before launch" list, ordered by legal risk

Do not invent policy text. The output is the engineering input the policy author needs.

$ARGUMENTS
