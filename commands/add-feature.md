---
name: add-feature
description: Scaffold a full vertical slice — table → endpoint → page in order, matched to a tier (free-on-signup / free-window / paid-only / admin-only). Use when adding a WHOLE new feature; for a single layer use /add-table, /add-endpoint, or /add-page.
---

A vertical slice. Description: $ARGUMENTS

## Gather from the user first

- Feature name
- Fields and their types
- Where it belongs in the product
- Tier: free-on-signup, free-window, paid-only, admin-only
- AI involved?

## Then run, in this order, awaiting confirmation before each step

1. **`/add-table`** — DB layer first; everything downstream depends on the schema. Apply the migration and verify columns landed before continuing.
2. **`/add-endpoint`** — API layer; match the tier from the user's input to the correct access-gate variant.
3. **`/add-page`** — UI layer; reuse the project's shared components.

Each step verifies before moving on (type check, migration applied + verified, route reachable).

## What "good" looks like

The new feature reads like a copy of the nearest existing feature in the same tier, with only the schema and prompt body different. Anything novel should be a deliberate, named choice.
