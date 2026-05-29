---
name: add
description: Router for the literal form `/add <endpoint|page|table|webhook|feature> <desc>` — dispatches to the matching /add-<layer> command and carries the shared discover-before-scaffolding pass. NOT a natural-language catch-all: prefer the specific command directly (/add-endpoint, /add-page, /add-table, /add-webhook, /add-feature).
---

Scaffold a new piece of the project. First token in `$ARGUMENTS` is the layer — read the matching command file IN FULL and follow it:

- `endpoint` → `/add-endpoint` — API route
- `page` → `/add-page` — UI page
- `table` → `/add-table` — DB table + migration
- `webhook` → `/add-webhook` — inbound provider webhook receiver (Stripe, etc.)
- `feature` → `/add-feature` — composite: table → endpoint → page

If the first token isn't one of these, ask the user which layer before proceeding.

(These were one file historically; they're now split so invoking one layer doesn't load the other four. If you arrived here directly, jump to the per-layer file above.)

---

# Universal — discover before scaffolding

Every layer starts here. Skip this and your scaffolding will recommend abstractions that already exist under different names, or invent patterns the codebase has already rejected.

Identify, by reading `package.json` and skimming nearby existing examples:

| What | Where it usually lives / search terms |
|---|---|
| Framework + router | `src/app/`, `pages/`, `routes/`, `src/routes/` |
| Validation library + schemas | `validation`, `schemas`, `zod`, `valibot` |
| AI output schemas (if AI) | `ai/schemas`, `prompts`, `llm` |
| Auth helper | `getAuthUser`, `requireUser`, `getServerSession` |
| CSRF / origin helper | `checkOrigin`, `verifyCsrf`, `sameOrigin` |
| Rate-limit helper | `rateLimit`, `limiter`, `throttle` |
| Access gate helper(s) | `requirePaidAccess`, `requireAccess`, `checkSubscription` |
| Idempotency | `idempotencyKey`, `dedupe`, `requestId` |
| Migration tool | `supabase/migrations/`, `prisma/migrations/`, `drizzle/`, flyway, dbmate |
| Generated DB types | `types/database.ts`, `db/schema.ts`, or wherever the regen lands |
| Authorization model | RLS policies vs app-level middleware vs RBAC table |
| Styling system | Tailwind, CSS Modules, styled-components, vanilla |

**Read one nearby existing example end-to-end. That's the template.** Match its shape unless there's a deliberate reason not to. Each `/add-<layer>` file repeats a compact version of this for standalone use.
