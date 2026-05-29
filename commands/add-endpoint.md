---
name: add-endpoint
description: Scaffold a new API route — schemas, handler order (origin→auth→rate-limit→validate→gate→idempotency→logic), raw+derived writes, PII-safe logging. Use for adding ONE backend endpoint. For a provider→server callback use /add-webhook; for a whole feature use /add-feature.
---

Scaffold a new API endpoint. Description: $ARGUMENTS

## Discover first

Read `package.json`, then grep for the project's helpers — validation/schemas, auth (`getAuthUser`/`requireUser`/`getServerSession`), origin/CSRF (`checkOrigin`), rate-limit, access gate (`requirePaidAccess`/`requireAccess`/`checkSubscription`), idempotency, generated DB types. **Read one nearby sibling endpoint end-to-end — that's your template.** Match its shape unless there's a deliberate reason not to.

## Schemas

- **Request** in the validation layer. Match the strictness of nearby schemas. Required, optional, `.max()`, refinements.
- **Response** explicit. If the endpoint returns AI output, validate the model's output against a separate output schema before sending.
- **Strings**: `.trim().min(1)` on every required string (user input or AI output). Whitespace passes truthy checks.

## Handler order

Same order, every time:

1. **Origin / CSRF check** — covers mutating endpoints and enumeration GETs. For same-origin downloads where `Origin` is absent, accept `Sec-Fetch-Site: same-origin|none`.
2. **Authentication** — extract the user from the server-side session. Never read `userId` from the request.
3. **Rate limit** — per-minute burst AND per-day cap. Per-day stops compromised sessions from scraping.
4. **Schema validation** of the parsed body. 400 on failure with field-level errors (omit values).
5. **Access gate** — see "Access gates" below.
6. **Idempotency check** if the operation is non-idempotent and retryable.
7. **Business logic.** Every DB query filters by the authenticated user id.

## Access gates

The rule: **gating is a centralized helper, never inlined.** Drift between inlined checks is exactly what helpers prevent.

- Find the helper(s) by grep: `requirePaidAccess`, `requireAccess`, `requireSubscription`, `gatePaid`, `hasAccess`, or similar.
- Match the helper to the feature's tier — paid-only vs free-window vs no-gate. Don't paste a paid-only gate on a free-tier feature.
- If you find inlined checks instead of a helper, that's an architectural finding — propose creating the helper before continuing.

**Routes that must NOT be gated:**
- Auth callback / session refresh
- The endpoint that *creates* the subscription
- Onboarding writes that run before the user can pay
- Webhook receivers (use signature verification instead)
- Admin routes (use the admin helper, not the paid gate)

## Data-write patterns

- **Raw before derived.** Insert raw first, then derived with AI/computed field `null`, then call the model, then UPDATE derived. Recoverable on model failure.
- **Inspect `.error` on every DB call** — apply **DB-ERROR-CHECK** (`~/.claude/REVIEWER_CONVENTIONS.md` §6): `{ data, error }` returns don't throw on RLS/schema-drift/outage, and a `try/catch` won't catch them. Same for `Promise.all` over writes — collect results and inspect each.
- **No fire-and-forget before a cache invalidation.** Await if a derived row must reflect the mutation.

## Observability and PII

- Catch and capture via the project's error sink. Latch per-request capture paths with a cooldown so a degraded upstream doesn't exhaust the quota.
- Never log request body, AI prompts, or any user-text field.
- Verify the sink scrubs `event.exception.values[*].value` — third-party SDK errors (Anthropic, OpenAI, Stripe) echo the request body in the error message.

## Deployment-time hazards (catch at scaffold)

- New env var? Note that it must be set in the deploy target before this endpoint can ship.
- New external API call? Add the provider to the sub-processor list and update the privacy policy if user data flows to it.

## Verify

Type check. Read the diff: 6 steps in order, no helper bypassed, no inlined gate.
