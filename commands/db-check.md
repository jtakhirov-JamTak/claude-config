---
name: db-check
description: Verify a migration ACTUALLY applied on the live DB — parse the migration's expected schema objects, generate one information_schema verification query with a hard count, and produce copy-paste remediation. Use after applying a migration on Supabase/Postgres, or when "column does not exist" errors hit production despite the migration "running".
---

Verify that a migration's schema changes actually landed on the target database. This exists because **idempotent `add column if not exists` blocks are silently skippable** — when SQL is pasted into a web editor and only part of it is highlighted-and-run, the skipped statements report no error and the migration looks "applied" while a column is missing. The symptom is a production write failing with `column ... does not exist` even though the migration file is in `main` and was "run twice."

Argument (`$ARGUMENTS`): a migration file path, a migration number, or empty (defaults to the most recent migration on disk). May also name specific tables/columns to check directly.

## Step 1 — Determine the expected schema objects

- If given a migration file/number, read it. If empty, find the highest-numbered file under the migrations dir (`supabase/migrations/`, `prisma/migrations/`, `drizzle/`, etc.) and read it.
- Extract every schema object the migration is supposed to create:
  - `ALTER TABLE x ADD COLUMN [IF NOT EXISTS] col ...` → expect `(x, col)`
  - `CREATE TABLE [IF NOT EXISTS] x ...` → expect table `x` + each column
  - `CREATE [UNIQUE] INDEX [IF NOT EXISTS] i ...` → expect index `i`
  - `CREATE POLICY p ON x ...` / `ENABLE ROW LEVEL SECURITY` → expect policy / RLS flag
- **Ignore `comment on ...` statements** — comments aren't schema objects `information_schema` tracks as present/absent, and a missing comment is not a functional bug. Tell the user explicitly: "this checks the N columns/tables/indexes the migration creates, not the M comment statements." Comments that target *pre-existing* columns are doubly out of scope.
- Build the **expected set** as an explicit list with a known total count. State the count out loud — it's the number the verification query must return.

## Step 2 — Generate the verification queries

Emit TWO queries the user runs once each. The **assertion** query is primary — it returns a single PASS/FAIL row so the user never has to count by hand (manual counting is the exact error that the partial-paste incident turned on). The **listing** query shows *which* object is missing when the assertion fails.

Assertion (one row — read the `status` cell):

```sql
-- status should read 'OK'. Anything else = a statement was skipped (usually a partial paste).
select count(*) as found, <N> as expected,
       case when count(*) = <N> then 'OK'
            else 'MISSING ' || (<N> - count(*))::text end as status
from information_schema.columns
where (table_name, column_name) in (
  ('prepare_entries','neutral_check_question'),
  ('prepare_entries','default_pattern')
  -- ...one tuple per expected (table, column)
);
```

Listing (run only if status isn't OK — shows what landed so you can see the gap):

```sql
select table_name, column_name
from information_schema.columns
where (table_name, column_name) in ( /* same tuples */ )
order by table_name, column_name;
```

For indexes: `select indexname from pg_indexes where indexname in (...);`
For RLS: `select relname, relrowsecurity from pg_class where relname in (...);`
For policies: `select policyname, tablename from pg_policies where tablename in (...);`
For table existence: `select to_regclass('public.<table>') is not null;`
For FK delete rules (esp. verifying `on delete cascade` to `auth.users` — e.g. before trusting an account-deletion cascade): use **`pg_constraint`, NOT `information_schema`**. `information_schema.referential_constraints` / `constraint_column_usage` HIDE constraints that reference `auth.users` from the query role (privilege filtering) and return empty — a silent false negative. Use:

```sql
select con.conrelid::regclass as table_name,
       case con.confdeltype when 'c' then 'CASCADE' when 'a' then 'NO ACTION'
            when 'n' then 'SET NULL' when 'r' then 'RESTRICT' else con.confdeltype::text end as on_delete
from pg_constraint con
join pg_class rel on rel.oid = con.confrelid
join pg_namespace nsp on nsp.oid = rel.relnamespace
where con.contype = 'f' and nsp.nspname = 'auth' and rel.relname = 'users';
```

## Step 3 — Generate copy-paste remediation

For each object that could be missing, emit a self-contained, idempotent remediation block ending in a PostgREST cache reload. Crucial for Supabase: a column can exist but the API still 500s for up to ~10 min on a stale schema cache, so **always pair the DDL with the reload**:

```sql
alter table public.<table> add column if not exists <col> <type>;
comment on column public.<table>.<col> is '<what it is>';  -- if the migration set one
notify pgrst, 'reload schema';
```

Then re-run the Step 2 verification query to confirm the count is now correct.

## Step 4 — Walk the (likely non-technical) user through it

The user typically pastes into the Supabase SQL Editor. Be explicit:

1. "Paste the **assertion** query below and run it. Read the `status` cell: it should say **`OK`**. If it says `MISSING n`, that many statements were skipped — almost always a partial paste."
2. "If it's not OK, run the **listing** query to see which objects landed, then run the remediation block."
3. "Re-run the assertion query until `status` reads `OK`."
4. Only after `status` is `OK`: "Test the action that was failing — it should work now."

## Step 5 — If a Supabase MCP / CLI is connected, do it directly

If the Supabase MCP server or CLI is authenticated in this session, run the verification query yourself and report the actual vs expected count instead of asking the user to paste. If not, produce the copy-paste blocks above — never claim a migration is verified that you couldn't actually query.

**Do NOT trust a migration-tracking table as proof.** Supabase `list_migrations` (and `supabase_migrations.schema_migrations`) stays EMPTY when migrations are applied by pasting SQL into the web editor — the common case for a non-technical operator. An empty list does NOT mean "nothing applied"; it means the tracker wasn't used. Always verify the actual schema OBJECTS (`information_schema` / `pg_constraint` / `to_regclass`), never the tracker. (Confirmed 2026-06-08: `list_migrations` returned `[]` while all 45 migrations' objects were present on the live DB.)

## Output

- The expected-objects list with its total count.
- The assertion + listing queries (Step 2).
- Remediation block(s) for anything that might be missing (Step 3), each ending in `notify pgrst, 'reload schema';`.
- A one-line verdict: `VERIFIED (<N>/<N> present)`, `INCOMPLETE (<M>/<N> — run remediation)`, or `UNVERIFIED (no DB access — user must run the query)`.

## Note for migration authors

The durable fix is to make every migration self-verifying: append a final `DO $$ BEGIN IF (select count(*) ... ) <> <N> THEN RAISE EXCEPTION '...'; END IF; END $$;` block so a partial paste *errors loudly* instead of silently succeeding. Suggest adding this to the migration template if the project doesn't have it.
