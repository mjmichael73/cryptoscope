# Spec — Phase 5: Frontend Polish

Date: 2026-11-15
Status: Approved (design Q&A 2026-11-15)
Scope: Frontend auth, watchlist/alert management UIs, missing backend CRUD endpoints, SSE hardening, responsive layout, frontend test infrastructure, docs.

## Context

Roadmap Phases 1–4 are complete. Phase 5 ("Frontend polish") is untouched: the
frontend has no authentication, the Watchlists page fakes its list by deriving
entries from alert rules, alert rules cannot be deleted, and there is no
frontend test infrastructure (`make lint-frontend` is only `tsc --noEmit`).

Facts established during exploration that constrain this design:

- The api-gateway validates Keycloak RS256 JWTs (`internal/auth/jwt.go`),
  requires a `tenant_id` claim, and forwards `X-Tenant-Id`/`X-Tenant-Slug`.
  In `DevMode` it skips validation and injects `demo-tenant`.
- Keycloak is **not** in the dev compose today.
- The command service requires an `Idempotency-Key` header on POSTs
  (`app/api/deps.py`), but the frontend never sends one — every create from
  the UI currently fails against the real backend. This is a live bug this
  phase fixes.
- Backend CRUD gaps: watchlists have only `POST /v1/watchlists`; alert rules
  have only `POST` (create) and `GET` (alert-service). No list/delete for
  watchlists, no delete for rules, no clear-history for triggers.
- Real-time candles already stream over SSE (`StreamHub` → `useCandleStream`).
- The demo tenant referenced by `scripts/bootstrap.sh` (`demo-tenant`) is not
  a UUID and has no seeded row; `watchlists.tenant_id` is a UUID FK to
  `tenants.id`, so bootstrap silently fails on Postgres today.

## Decisions (agreed with the product owner)

1. **Auth = Keycloak OIDC + PKCE** in the frontend, with a one-click dev-mode
   demo login (gated by `VITE_DEV_AUTH=1`) that mirrors the gateway's existing
   dev-bypass philosophy. Keycloak joins the dev compose so the real flow is
   exercisable.
2. **Real-time stays SSE.** The WebSocket roadmap item is resolved-by-SSE; we
   harden the existing hook (auto-reconnect with backoff) instead of adding a
   second transport.
3. **Add the missing backend endpoints** (watchlist list/update/delete, alert
   rule delete, trigger history clear) so the management UIs are real CRUD,
   not mockups.

## Goals

- A user can log in through Keycloak (or one click in dev), stay logged in
  across the SPA session, and be logged out cleanly.
- Watchlists and alert rules are fully managed from the UI against real data.
- Trigger history can be cleared (acknowledged-only or all).
- The UI is usable on a phone-sized viewport.
- The frontend has a real test suite that runs via `make test-frontend` and is
  part of `make test`.
- All new backend behavior is covered by Python and Go tests in the existing
  dockerized test harness.

## Non-goals

- Editing existing alert rules (create + delete only; edit adds form
  complexity disproportionate to value this phase).
- Production Keycloak deployment automation (realm JSON + compose wiring only;
  production cluster setup remains documented, not scripted).
- WebSocket transport.
- Fixing the legacy `demo-tenant` non-UUID dev bypass beyond what the demo
  login needs (noted in Risks).

## Architecture

### 1. Authentication

```
Browser SPA ──(1) 302──► Keycloak /authorize (PKCE S256)
      ▲                   realm: cryptoscope, public client "cryptoscope-frontend"
      │──(2) /callback?code──► SPA exchanges code+verifier at /token via nginx
      │──(3) Bearer JWT on every /api call──► gateway validates (existing)
```

**Frontend** (`frontend/src/auth/`):

- `oidc.ts` — pure, DOM-free helpers: `createPkcePair()` (verifier +
  S256 challenge), `buildAuthorizeUrl()`, `exchangeCode()`, `refreshToken()`,
  `decodeJwt()` (payload-only base64url decode for display purposes; trust
  always comes from the gateway's validation, never from client-side checks).
- `storage.ts` — `sessionStorage`-backed token store (`access_token`,
  `refresh_token`, `expires_at`, id token for logout redirect). Keys namespaced
  `cryptoscope.auth.*`.
- `AuthContext.tsx` — provider exposing `{user, token, status, login(),
  logout()}`. On mount with a stored token: if expired → refresh; schedules
  refresh 60 s before `expires_at`. `logout()` clears storage and redirects to
  Keycloak `end_session_endpoint` when configured.
- `RequireAuth.tsx` — route wrapper: unauthenticated → redirect `/login` with
  `state.from` preserved.
- `Login.tsx` — "Sign in with Keycloak" button (redirect) and, when
  `import.meta.env.VITE_DEV_AUTH === "1"`, a "Demo login" button that mints a
  local session (no network).
- `Callback.tsx` — reads `code`/`state`, validates state against the value
  stored at redirect, exchanges via POST `{issuer}/token` through the nginx
  `/auth/` proxy, stores tokens, navigates to `state.from ?? "/"`.
- `api/client.ts` — attaches `Authorization: Bearer …` from the token store;
  generates a UUID `Idempotency-Key` per mutating request (fixes the live
  bug); on 401 → single refresh → retry once → otherwise emit logout.

**Config (Vite env)**: `VITE_OIDC_ISSUER` (default
`/auth/realms/cryptoscope` — the nginx-proxied same-origin path),
`VITE_OIDC_CLIENT_ID` (default `cryptoscope-frontend`), `VITE_DEV_AUTH`.

**Gateway / infra**:

- `deploy/keycloak/realm-export.json` — realm `cryptoscope`; public client
  `cryptoscope-frontend` (standard flow, PKCE required, redirect
  `http://localhost:5173/*` + `http://localhost:8080/*`); demo user
  `demo@cryptoscope.local` / password from `KEYCLOAK_DEMO_PASSWORD` (default
  `demo-password`); a `tenant_id` + `tenant_slug: demo` claim mapper on the
  client scope so the JWT carries tenancy exactly as the gateway expects.
  The mapper's `tenant_id` is the fixed demo UUID
  `11111111-2222-3333-4444-555555555555` (grep-able constant, must equal the
  seeded tenant row).
- `docker-compose.yml` — `keycloak` service (Quarkus dev-opted image, realm
  import, internal port 8080, published on host port 8081), dev profile only.
- `frontend/nginx.conf` — `location /auth/ { proxy_pass
  http://keycloak:8081/auth/; }` in the prod image; `vite.config.ts` gets the
  matching dev-server proxy entries (`/api` → gateway, `/auth` → keycloak) so
  both dev modes behave identically.
- Migration `0005_demo_tenant.py` (command service) — seeds the fixed demo
  tenant row (UUID `11111111-2222-3333-4444-555555555555`, slug `demo`) so
  FKs resolve; idempotent via fixed primary key.

### 2. Backend CRUD additions

**command-service** (`/v1`, tenant from verified header, idempotency unchanged
for creates):

| Method | Path | Behavior |
|---|---|---|
| GET | `/v1/watchlists` | list caller's watchlists, newest first |
| GET | `/v1/watchlists/{id}` | single (404 if other tenant's) |
| PUT | `/v1/watchlists/{id}` | rename / replace symbol list; emits `watchlist_updated` |
| DELETE | `/v1/watchlists/{id}` | emits `watchlist_deleted`; 404 if not owned |
| DELETE | `/v1/alert-rules/{id}` | sets rule `status=deleted` (soft) + emits `alert_rule_deleted`; historical triggers preserved |

**alert-service**:

| Method | Path | Behavior |
|---|---|---|
| DELETE | `/v1/triggers` | clears history; `?acknowledged_only=true` limits to acknowledged rows; returns `{"deleted": n}` |
| consumer | `alert_rule_deleted` | marks the rule row `status=deleted` in the shared table so evaluation skips it |

Note: command- and alert-service share the `alert_rules` table, so the
command-side soft delete is already visible to the engine; the consumer
handler is a defensive consistency measure (e.g. re-processing a missed
event after outages) and keeps event vocabulary uniform.

**Shared lib** (`cryptoscope_shared.events`): add `WATCHLIST_UPDATED`,
`WATCHLIST_DELETED`, `ALERT_RULE_DELETED` constants.

**gateway** (`internal/gateway/gateway.go`): route all new endpoints through
`authMW` + `RateLimitMiddleware`, proxying to command/alert as appropriate.
Go tests cover routing, tenant scoping (404 cross-tenant), and auth
requirements (401 without token in prod mode).

**Frontend client** gains: `listWatchlists`, `getWatchlist`,
`updateWatchlist`, `deleteWatchlist`, `deleteAlertRule`, `clearTriggers`.

### 3. Pages

- **Watchlists.tsx** — rewritten: real list (name, symbol chips, created
  date), create form (kept), edit (inline rename + symbol edit), delete with
  confirm. No more alert-rule-derived fake data.
- **AlertRules.tsx** — creation form kept as-is; adds a rules table below
  (symbol, comparator label, threshold, interval, status, created) with a
  delete action per row.
- **AlertTriggers.tsx** — adds a "Clear acknowledged" button (and "Clear all"
  behind confirm) next to the existing filter tabs.
- **Layout.tsx** — user menu in the header (username from JWT, logout);
  mobile hamburger drawer for nav; content grids collapse to single column
  under `sm`.
- **useCandleStream.ts** — auto-reconnect with exponential backoff (1 s → 30 s
  cap, jitter), reconnect counter exposed to the UI badge in MarketData.

### 4. Testing

**Frontend (new infra)**: vitest + @testing-library/react + jsdom +
`@testing-library/user-event`; `npm run test` → `vitest run`; new
`test-frontend` service in `docker-compose.tests.yml` (node:22-alpine, `npm ci`
then `vitest run`); `make test-frontend` target added to `Makefile` and to the
`test` aggregate. Coverage:

- `oidc.ts`: PKCE pair shape/S256 correctness, authorize URL params, state
  handling, token exchange request shape, refresh.
- `storage.ts`: round-trip, clear.
- `AuthContext`: session restore, expiry refresh scheduling, 401 → refresh →
  retry → logout path (with a mocked fetch).
- `client.ts`: Authorization + Idempotency-Key headers attached; 401 retry
  once.
- `RequireAuth`/`Login`/`Callback`: redirect, state validation, error state.
- Pages: Watchlists CRUD flows, AlertRules create/delete, AlertTriggers
  filter/ack/clear — against a mocked `client` module.

**Python**: command-service route tests for the five new endpoints (happy
path, cross-tenant 404, validation, idempotent replay unaffected); alert-service
tests for trigger clear (all / acknowledged-only) and the
`alert_rule_deleted` consumer path (rule skipped afterwards).

**Go**: gateway tests for new routes (auth required, tenant forwarded,
proxying correct upstream).

### 5. Documentation

- `docs/roadmap.md` — Phase 5 checked off; WebSocket item annotated
  "resolved by SSE streaming"; success-criteria table refreshed.
- `docs/CHANGELOG.md` — Unreleased section entries.
- `docs/API.md` — new endpoints + auth requirements.
- `docs/DEPLOYMENT.md` — Keycloak dev service, frontend env vars, realm
  import, nginx `/auth/` proxy.
- `docs/security.md` — OIDC/PKCE flow, token storage choice and trade-offs.
- `docs/guides/usage.md` — login walkthrough, watchlist/rule management.
- `AGENTS.md` — frontend test commands (`make test-frontend`).

## Risks / notes

- **sessionStorage tokens**: XSS-readable by design trade-off; acceptable for
  this phase because the gateway validates every request server-side and the
  app has no third-party scripts. Documented in security.md; refresh rotation
  via Keycloak keeps windows short.
- **Demo tenant UUID**: the Keycloak claim mapper and migration `0005` must
  use the same fixed UUID (constant documented in both files).
- **Legacy dev bypass**: gateway `DevMode` still injects non-UUID
  `demo-tenant`; unchanged behavior, but noted — a future phase should unify
  dev identity with the Keycloak demo user.
- **Idempotency-Key on PUT/DELETE**: creates keep the header requirement;
  updates/deletes are naturally idempotent and do not require it (gateway and
  services agree on this).
