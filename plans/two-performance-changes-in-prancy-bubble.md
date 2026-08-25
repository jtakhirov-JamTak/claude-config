# Preconnect guard + legacy-polyfill finding

## Context

Two performance changes were requested. Investigation during planning found that **both had
already landed** in commit `0c205f9` (2026-07-28, "Preconnect to Supabase; document browser
floor; sign-in prerender tests"), and that the stated rationale for one of them is
empirically false. The scope below is what actually remains.

**Item 1 — legacy polyfills.** `browserslist` is already at `package.json:8-14`, as a
superset of the requested list (adds `edge >= 111` and `ios_saf >= 16.4`, which browserslist
does *not* infer from `chrome`/`safari` — `ios_saf` is the real target for a mobile PWA).
`ARCHITECTURE.md:156` records that builds before and after were byte-identical.

Chasing the real cause resolved it during planning. Chunk `838` **is** in the root shell
(so it does count against the 178 KiB budget), and its polyfill payload is webpack module
`8456`, which is byte-for-byte `node_modules/next/dist/build/polyfills/polyfill-module.js`:

```
"trimStart"in String.prototype||(String.prototype.trimStart=String.prototype.trimLeft),
"trimEnd"in String.prototype||(...),"description"in Symbol.prototype||...,
Array.prototype.flat||... ,Array.prototype.flatMap||... ,Object.fromEntries||... ,Object.hasOwn||...
```

That is exactly the audit's flagged list. Three consequences:

- It is **Next framework code injected unconditionally** into the client entry, not SWC
  transpilation output. No compiler target — `browserslist` included — removes it. Removing
  it would mean aliasing a framework internal path in webpack config: unsupported, and out
  of proportion to the payoff.
- **The file is 1380 bytes raw** (a few hundred gzipped), not ~12 KiB. Lighthouse's
  `legacy-javascript` audit reports estimated savings for the whole matched chunk, so the
  ~12 KiB figure substantially overstates the actual polyfill payload.
- The es-shims packages in the lockfile (`string.prototype.trimstart`, `object.fromentries`,
  `array.prototype.flat`) are **dev-only**, reachable solely via `eslint-config-next`. They
  are not in the client bundle and are not the source. Verified with `npm ls`.

So item 1 ships **no code change** — only a documentation correction so this is not
re-attempted a third time.

**Item 2 — preconnect.** The preconnect exists at `src/app/layout.tsx:43` as a JSX
`<link rel="preconnect" href={supabaseOrigin} crossOrigin="anonymous" />` inside an explicit
`<head>`. It has **no localhost/placeholder guard**, which is the genuine remaining delta:
today every dev build emits a preconnect to `http://127.0.0.1:54321`, and every hermetic
CI/e2e build emits one to `https://example.supabase.co` — a host that does not resolve to a
real Supabase, so the browser opens a connection attempt that can never be reused.

## Changes

### 1. New pure helper — `src/lib/env/preconnect-origin.ts`

Extracting the guard as a pure function makes it unit-testable with **zero mocks** in the
existing `environment: "node"` vitest setup. This follows the `src/app/sw.test.ts` precedent
(pure predicate extracted from the module that consumes it) and avoids the module-scope
`clientEnvSchema.parse()` in `src/lib/env/client.ts:13`, which otherwise forces
`vi.resetModules()` gymnastics to vary the URL.

```ts
// Returns the origin to preconnect to, or null when warming it would be wasted:
// a local Supabase stack needs no DNS/TLS handshake, and the hermetic-test
// placeholder host does not resolve to a real Supabase — the browser would open a
// connection the real request can never reuse.
export const PLACEHOLDER_SUPABASE_HOST = "example.supabase.co";

export function preconnectOrigin(url: string): string | null {
  const { origin, hostname } = new URL(url);
  if (hostname === "localhost" || hostname === "127.0.0.1" || hostname === "[::1]") return null;
  if (hostname === PLACEHOLDER_SUPABASE_HOST) return null;
  return origin;
}
```

Matching on `hostname` (not `startsWith` on the whole URL) means the port and any path are
correctly ignored — `.env.example` ships `http://127.0.0.1:54321`, and the placeholder is
referenced with and without a path across the repo.

`new URL(...)` cannot throw here: `src/lib/env/client.ts:9` validates
`NEXT_PUBLIC_SUPABASE_URL` with `z.url()` at import time.

### 2. `src/app/layout.tsx` — render the link conditionally

Keep the existing JSX `<link>` and explicit `<head>`; only gate it. The comment at lines 8-13
stays (it explains *why* the preconnect exists and why `crossOrigin="anonymous"` is required);
add a line pointing at the helper for the *when-not* case.

```tsx
const supabaseOrigin = preconnectOrigin(clientEnv.NEXT_PUBLIC_SUPABASE_URL);
...
<head>
  {supabaseOrigin !== null && (
    <link rel="preconnect" href={supabaseOrigin} crossOrigin="anonymous" />
  )}
</head>
```

Use `!== null` rather than `&&` on the string so the guard reads as intended and cannot
render a stray empty string.

### 3. Tests

**Unit — `src/lib/env/preconnect-origin.test.ts`** (new). Node env, no mocks, imports
`describe/it/expect` from `"vitest"` per house style:

- real cloud URL (`https://abcdefg.supabase.co`) → returns the origin
- `http://127.0.0.1:54321` → `null` (the `.env.example` dev default)
- `http://localhost:54321` → `null`
- `https://example.supabase.co` and `https://example.supabase.co/rest/v1` → `null`
- a real URL with a path/port → origin only, path stripped

**E2E — `e2e/auth-shell.spec.ts`**, added inside the existing `test.describe("sign-in
prerender")` block (lines 118-140) that already runs with `test.use({ javaScriptEnabled:
false })`, so it observes exactly the server-delivered HTML:

```ts
await expect(
  page.locator(
    'link[rel="preconnect"][href*="127.0.0.1"], link[rel="preconnect"][href*="localhost"], link[rel="preconnect"][href*="example.supabase.co"]',
  ),
).toHaveCount(0);
```

Asserting **absence of a local/placeholder preconnect** rather than presence of any
preconnect is deliberate: `playwright.config.ts:43-44` falls back to the placeholder, but a
local `.env.local` pointing at `http://127.0.0.1:54321` wins over it, and CI's `quality` job
uses a localhost URL. This assertion is correct under all three, and would still pass — while
remaining meaningful — if someone ran e2e against a real cloud project.

### 4. Docs — `ARCHITECTURE.md` (no Fix Log rows)

Neither change is a bug ported from a downstream app, which is what the Foundation Fix Log
records (`.claude/ENGINEERING_PLAYBOOK.md:50-51`). Both belong in the decision log:

- **Line 155** (preconnect): append the guard rationale — suppressed for localhost/`127.0.0.1`
  and the `example.supabase.co` placeholder, because a local stack needs no handshake and the
  placeholder opens a connection the real request can never reuse.
- **Line 156** (browserslist): replace the "builds were byte-identical" explanation with the
  *measured cause* — Lighthouse's `legacy-javascript` flag on chunk 838 is Next's own
  `next/dist/build/polyfills/polyfill-module.js` (1380 bytes raw), injected unconditionally
  and unaffected by any compiler target; the ~12 KiB is the audit's whole-chunk estimate, not
  the polyfill's real size. Keep the existing "do not cite this key as a bundle-size measure"
  directive.

### Deliberate non-change

`e2e/global-setup.ts:10,33` keeps its own local copies of the placeholder URL and the
localhost predicate. It is a Playwright-side file outside `src/`, it needs the *predicate*
rather than an origin, and wiring `@/`-alias resolution into the Playwright transform for one
string is more coupling than the duplication costs.

## Verification

1. `npm run verify` — full gate (format, typecheck, lint, vitest, build, bundle, sw, secrets,
   analytics). The new unit test runs under `npm run test`.
2. `npm run test:e2e` — both mobile projects; the new assertion lands in the JS-disabled
   prerender block.
3. **`check:bundle` will NOT report a smaller total.** It should stay at ~161.8 KiB gzip
   across 12 chunks against the 178 KiB budget. No bytes were removed by either item — the
   guard only affects dev/CI builds, and the polyfill is framework-injected. Do not adjust the
   budget; a *changed* number here means something unintended happened and should be
   investigated before committing.
4. Spot-check the built HTML directly, since the guard is invisible to a normal prod build:
   `grep -c preconnect .next/server/app/index.html` should be **0** after a build with the
   placeholder or a localhost URL, and **1** after a build with a real cloud
   `NEXT_PUBLIC_SUPABASE_URL`.

## Working-tree note

`src/app/(public)/sign-in/page.tsx` and `sign-in-form.tsx` show as modified but are
byte-identical to HEAD (`git diff HEAD` is empty) — stale index stat entries left by the
revert documented in the last Fix Log row. Do not include them in the commit. `.archive/` is
untracked local session state.

Heed the standing directive in that row: **do not re-attempt the `useSearchParams()`/Suspense
extraction on `/sign-in` for LCP reasons** — it was measured as a regression (2193 → 2269 ms).
