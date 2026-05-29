---
name: add-table
description: Scaffold a new DB table + migration — owner FK/cascade, indexes, RLS policies, constraints (dedup CTE, >= on timestamps, backfill before NOT NULL/CHECK), data-classification comments, type regen. Use for adding ONE table.
---

Scaffold a new table + migration. Description: $ARGUMENTS

## Discover first

Find the migration tool (`supabase/migrations/`, `prisma/`, `drizzle/`, flyway, dbmate), the generated-types target (`types/database.ts`, `db/schema.ts`), and the authorization model (RLS policies vs app-level). **Read one nearby existing migration end-to-end — that's your template.**

## Define the table

Required columns on any user-scoped table:

- **Owner FK** — `user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE` (or the project's equivalent). Without cascade, account deletion leaves orphans.
- **`created_at`** — `TIMESTAMPTZ NOT NULL DEFAULT now()`.
- **`updated_at`** — only if rows mutate after insert.
- **Indexes** — on every filterable / sortable column. At minimum the owner FK. `(user_id, created_at DESC)` is common.

If the table stores a computed snapshot:
- **`generator_version`** — text or int stamped by the code version that produced the snapshot. Readers filter on it; writers stamp it. Bumping invalidates stale rows without a migration.

If the table has a state machine (`open`/`resolved`/`archived`):
- The status column should not be user-writable through the gateway path. Transitions go through dedicated mutation endpoints.

## Data classification

For sensitive columns, add a comment at column creation:
- `email TEXT NOT NULL, -- PII: email`
- `journal_text TEXT, -- SENSITIVE: journal content`

`/privacy-audit` finds these by grep instead of inferring from column names.

## Constraints

- **Timestamp pairs**: `>=` not `>` on `CHECK (end_at >= start_at)`. Clock equality on first-write is a real case.
- **`NOT NULL` on existing data**: backfill in the same migration before adding, OR add nullable, backfill, then alter in a follow-up.
- **`CHECK` on existing data**: validate or remediate violators in the same migration.
- **`UNIQUE` indexes**: prepend a dedup CTE — `CREATE UNIQUE INDEX IF NOT EXISTS` aborts the whole migration on the first duplicate.

```sql
WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (PARTITION BY user_id, name ORDER BY id) AS rn
  FROM things
)
DELETE FROM things WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

CREATE UNIQUE INDEX IF NOT EXISTS things_user_name_uq ON things (user_id, name);
```

## Row-level authorization

If the project uses RLS:

- **Enable RLS** on the table.
- **SELECT** — `USING (auth.uid() = user_id)`. Never `USING (true)`.
- **INSERT** — `WITH CHECK (auth.uid() = user_id)`. Add column-specific restrictions if some columns must be server-enforced (e.g. force `status = 'open'`).
- **UPDATE** — `USING (auth.uid() = user_id)`. Restrict which columns can change. **Never let users update an anchor column** (free-window start, status with transition rules, role).
- **DELETE** — only if user-initiated delete is supported. For anchor-bearing tables, dropping DELETE is correct.

If the project uses app-level authorization (no RLS), apply the same rules at the route layer.

## Apply and regenerate

- Apply to dev (and pre-prod if applicable).
- Regenerate the typed DB schema. Confirm the new types appear before consumers reference them.
- An unapplied migration in main is a deploy footgun — flag if you're committing without applying.
- After applying, run `/db-check` (or its verification query) to confirm every new column actually landed — idempotent `add column if not exists` blocks are silently skippable by a partial SQL-editor paste.

## Validation

If the table receives API writes, add request and (if applicable) output schemas in the validation layer. `null` vs `""` consistency: pick one for absent optional fields, apply across raw + derived + serialized.

## Verify

Apply the migration to a fresh DB to confirm idempotency. Query as user A while logged in as user B — confirm zero rows.
