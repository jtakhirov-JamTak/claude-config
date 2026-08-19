---
name: add-webhook
description: Scaffold an inbound provider webhook receiver (Stripe/payment/email) — raw-body signature verify, idempotent replay defense, NO auth/CSRF/paywall gate, ack-200 on unknown types. Use for a provider→server callback, NOT a user-facing endpoint (use /add-endpoint for those).
---

Scaffold an inbound webhook from a provider. Description: $ARGUMENTS

It is **not** a normal endpoint — most of the standard handler order is wrong here. A webhook is called by a _server_, not your logged-in user, so there's no session, no Origin, no CSRF, and it must NOT be paywall-gated. Its security model is the **signature**, not auth.

## Before scaffolding

Apply **DISCOVER-FIRST** (`~/.claude/REVIEWER_CONVENTIONS.md` §6) for the project-wide helper map, then the webhook-specific work:

- Read the provider's webhook docs for the exact signature scheme and the header it uses.
- Find how the project reads raw request bodies — signature verification needs the **raw bytes**, and frameworks that auto-parse JSON destroy them. (Next.js App Router: read `await req.text()` and verify before `JSON.parse`; never `await req.json()` first.)
- Find the dedup/idempotency store the project already uses.

## Handler order (different from a normal endpoint)

1. **Read the raw body** as text — do not parse yet.
2. **Verify the signature** against the raw body using the provider's SDK and the signing secret (server-side env var). Invalid/missing signature → `400`, log nothing sensitive, stop. This replaces auth + origin + CSRF.
3. **Parse** the now-trusted body.
4. **Idempotency / replay defense.** Providers retry and may deliver duplicates. Dedup on the provider's event id — record processed ids; if seen, ack `200` and do nothing. The same event twice must never double-grant entitlement or double-apply a side effect.
5. **Dispatch on event type.** Handle the types you care about; for unknown types, ack `200` (don't 4xx — that triggers provider retries forever).
6. **Mutate, inspecting `.error` on every write** (**DB-ERROR-CHECK**, `~/.claude/REVIEWER_CONVENTIONS.md` §6). Use the privileged/service client — there is no user session. This is the only place allowed to grant entitlement (`status = active`); a user-callable route must never do it. Writes must be idempotent (step 4) AND match the raw+derived discipline if a derived row is involved.
7. **Ack fast.** Return `200` quickly; do heavy work async if the provider has a tight ack timeout, but only after the state that makes the event safe-to-replay is committed.

## Must-NOTs (the easy ways to get this wrong)

- **No paywall/access gate.** Webhooks are deliberately un-gated — gating one means the provider's calls get 403'd and entitlements silently never apply. (**GATE-EXCLUSIONS**, `~/.claude/REVIEWER_CONVENTIONS.md` §6, lists webhook receivers as a correct gate _exclusion_ — keep it that way.)
- **No `req.json()` before verifying** — it eats the raw body the signature needs.
- **No trusting any field as identity** — the signature is the only trust boundary.
- **No 4xx on an event you simply don't handle** — ack 200 or the provider retries indefinitely.

## Deployment-time hazards (catch at scaffold)

- The signing secret is a new env var — must be set in the deploy target, and it differs between the provider's test and live modes.
- Register the endpoint URL in the provider's dashboard, and note which event types it must be subscribed to.
- New sub-processor / money flow → privacy policy + the subscription-lifecycle checks in `/deploy-check scope=full` apply.

## Verify

Type check. Re-send the same event twice (replay) and confirm the second is a no-op. Send a tampered/garbage signature and confirm `400`. Send an unhandled event type and confirm `200` no-op.
