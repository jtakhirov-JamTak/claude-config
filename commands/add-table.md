---
name: add-table
description: Scaffold a new DB table + migration — owner FK/cascade, indexes, RLS policies, constraints (dedup CTE, >= on timestamps, backfill before NOT NULL/CHECK), data-classification comments, type regen. Use for adding ONE table.
---

Scaffold a new table + migration. Description: $ARGUMENTS

## Discover first

Apply **DISCOVER-FIRST** (`~/.claude/REVIEWER_CONVENTIONS.md` §6), then narrow to this layer: the migration tool (`supabase/migrations/`, `prisma/`, `drizzle/`, flyway, dbmate), the generated-types target (`types/database.ts`, `db/schema.ts`), and the authorization model (RLS policies vs app-level). **Read one nearby existing migration end-to-end — that's your template.**

## Define the table

Required columns on any user-scoped table:

- **Owner FK** — `user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE` (or the project's equivalent). Without cascade, account deletion leaves orphans.
- **`created_at`** — `TIMESTAMPTZ NOT NULL DEFAULT now()`.
- **`updated_at`** — `TIMESTAMPTZ NOT NULL DEFAULT now()`, kept current by the canonical trigger, not by application code: `CREATE TRIGGER <table>_set_updated_at BEFORE UPDATE ON public.<table> FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();` (foundation standard: include it; rows almost always mutate eventually). Confirm `public.set_updated_at()` already exists in an earlier migration — a fresh-DB apply fails if the trigger runs before the function is defined.
- **`archived_at`** — `TIMESTAMPTZ` nullable, for soft delete. Include it whenever archive or delete semantics exist for the entity — for user-facing domain tables that is usually yes (foundation standard: archive rather than delete when history has value). It is a deliberate per-table decision, not free: **if `archived_at` exists, every list query, every RLS SELECT policy, and every export/deletion walk must filter on it** — otherwise archived rows leak into lists, or survive an account-deletion request. State the choice in the migration comment.
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

- **Uniqueness on a table with `archived_at`**: if an archived row must not block reuse of its value, filter the index instead of adding a constraint — a plain `UNIQUE` keeps the name reserved forever and users read that as a bug.

```sql
CREATE UNIQUE INDEX IF NOT EXISTS things_user_name_active_uq
  ON things (user_id, lower(name))
  WHERE archived_at IS NULL;
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
