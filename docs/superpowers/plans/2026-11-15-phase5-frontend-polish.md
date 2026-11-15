# Phase 5 — Frontend Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship all Phase 5 roadmap items — Keycloak OIDC auth with dev demo-login, real watchlist/alert CRUD UIs backed by new endpoints, SSE reconnect hardening, responsive layout, a frontend test suite, and updated docs.

**Architecture:** Frontend gains an `src/auth/` module (pure OIDC/PKCE helpers → storage → React context) that wraps the existing router; the API client attaches Bearer + Idempotency-Key headers. Backend gaps are filled with tenant-scoped CRUD endpoints in command-service and alert-service, routed through the gateway's existing auth+rate-limit middleware chain. Keycloak runs in the dev compose with a realm import that maps `tenant_id`/`tenant_slug` claims.

**Tech Stack:** React 19 + react-router 7 + Tailwind 4 (frontend), vitest + @testing-library/react (new), FastAPI/SQLAlchemy (Python services), chi (Go gateway), Keycloak 26 (quay.io/keycloak/keycloak).

**Spec:** `docs/superpowers/specs/2026-11-15-phase5-frontend-polish-design.md`

## Global Constraints

- Demo tenant UUID is exactly `11111111-2222-3333-4444-555555555555`, slug `demo` (Keycloak mapper, migration 0005, and tests all use this constant).
- New event type constants: `WATCHLIST_UPDATED = "watchlist_updated"`, `WATCHLIST_DELETED = "watchlist_deleted"`, `ALERT_RULE_DELETED = "alert_rule_deleted"` in `libs/python/cryptoscope_shared/events.py`.
- Every tenant-scoped query filters by `tenant_id`; cross-tenant reads return 404 (not 403).
- Deletes of alert rules are soft (`status="deleted"`); triggers are never deleted by rule deletion.
- Creates keep the `Idempotency-Key` requirement; PUT/DELETE do not require it.
- Go: `gofmt` + `go vet` clean; Python: `ruff` + `mypy` clean; frontend: `tsc --noEmit` clean.
- Structured logging only (slog / structlog); no print statements.
- Commits: concise, lowercase, no trailing period, author `Mojtaba Michael <mojimich2015@gmail.com>`, backdated with `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` starting `2026-11-15 15:00:00 +0000` and advancing per task.

## Review Focus

Failure modes the spec implies that task tests must pin:

1. **Dead refresh token** → AuthContext must log out cleanly on a failed refresh, never loop or hang on a broken page. Pinned in Task 9 (`refresh failure logs out`).
2. **Cross-tenant watchlist access by id** → 404, no data leak. Pinned in Task 2 (`get other tenant's watchlist returns 404`).
3. **Duplicate watchlist name within a tenant** → 409 conflict, no duplicate row. Pinned in Task 2.
4. **Gateway unreachable while streaming** → SSE hook retries with backoff capped at 30 s and reports `connected: false`, no infinite tight loop. Pinned in Task 14.
5. **Replayed create with same Idempotency-Key** → returns original resource id, no duplicate. Pinned in Task 2 (existing behavior must survive the refactor).

---

### Task 1: Shared event constants

**Files:**
- Modify: `libs/python/cryptoscope_shared/events.py`
- Test: `libs/python/tests/test_events.py` (create)

**Interfaces:**
- Produces: `WATCHLIST_UPDATED`, `WATCHLIST_DELETED`, `ALERT_RULE_DELETED` string constants (used by Tasks 2, 3, 5).

- [ ] **Step 1: Write the failing test** — `libs/python/tests/test_events.py`:

```python
from cryptoscope_shared.events import (
    ALERT_RULE_DELETED, WATCHLIST_CREATED, WATCHLIST_DELETED, WATCHLIST_UPDATED,
)

def test_new_event_type_constants():
    assert WATCHLIST_UPDATED == "watchlist_updated"
    assert WATCHLIST_DELETED == "watchlist_deleted"
    assert ALERT_RULE_DELETED == "alert_rule_deleted"
    assert WATCHLIST_CREATED == "watchlist_created"  # existing, unchanged
```

- [ ] **Step 2: Run** `docker compose -f docker-compose.tests.yml run --rm test-libs-python` — expect FAIL (ImportError).
- [ ] **Step 3: Implement** — add the three constants next to the existing ones in `events.py`.
- [ ] **Step 4: Run** again — expect PASS.
- [ ] **Step 5: Commit** `add watchlist update/delete and alert rule deleted event constants`

### Task 2: command-service watchlist CRUD (service + repo + routes)

**Files:**
- Modify: `services/command-service/app/domain/errors.py` (add `NotFoundError(RuntimeError)`)
- Modify: `services/command-service/app/domain/repository.py` (extend `WriteRepository` protocol)
- Modify: `services/command-service/app/domain/service.py` (add methods)
- Modify: `services/command-service/app/infra/repository.py` (implement new port methods)
- Modify: `services/command-service/app/domain/events.py` (add `watchlist_updated`, `watchlist_deleted` builders)
- Modify: `services/command-service/app/api/schemas.py` (add `WatchlistOut`, `UpdateWatchlistRequest`)
- Modify: `services/command-service/app/api/routes.py` (add 4 routes)
- Test: `services/command-service/tests/test_command_service.py`, `services/command-service/tests/test_routes_watchlists.py` (create)

**Interfaces:**
- Consumes: Task 1 event constants.
- Produces (service layer, all `async`):
  - `list_watchlists(tenant_id: str) -> list[Watchlist]` — newest first by `created_at`
  - `get_watchlist(tenant_id: str, watchlist_id: str) -> Watchlist` — raises `NotFoundError`
  - `update_watchlist(cmd: UpdateWatchlist) -> Watchlist` — `UpdateWatchlist(tenant_id, watchlist_id, name, symbols)`; validates non-empty name; raises `NotFoundError`; emits `watchlist_updated`
  - `delete_watchlist(tenant_id: str, watchlist_id: str) -> None` — raises `NotFoundError`; emits `watchlist_deleted`
- Produces (HTTP):
  - `GET /v1/watchlists` → `list[WatchlistOut]`
  - `GET /v1/watchlists/{id}` → `WatchlistOut` | 404
  - `PUT /v1/watchlists/{id}` → `WatchlistOut` | 404 | 422
  - `DELETE /v1/watchlists/{id}` → 204 | 404
- `WatchlistOut` fields: `id, tenant_id, name, symbols, created_at`. `UpdateWatchlistRequest`: `name: str`, `symbols: list[str]`.
- Repo port additions: `get_watchlist(tenant_id, watchlist_id) -> Watchlist | None`, `list_watchlists(tenant_id) -> list[Watchlist]`, `update_watchlist(watchlist) -> None` (flush), `delete_watchlist(watchlist) -> None` (session.delete + flush), `get_alert_rule(tenant_id, rule_id) -> AlertRule | None`, `soft_delete_alert_rule(rule) -> None` (set status, flush). Adapter methods filter by `tenant_id` in every query.

- [ ] **Step 1: Write failing service tests** in `test_command_service.py`: list returns newest-first; get unknown id raises `NotFoundError`; update renames + replaces symbols and publishes `watchlist_updated`; update unknown raises; delete removes and publishes `watchlist_deleted`; delete unknown raises; replayed create with same key still returns original id (regression).
- [ ] **Step 2: Run** `docker compose -f docker-compose.tests.yml run --rm test-command` — expect FAIL.
- [ ] **Step 3: Implement** service methods + repo port + adapter + events builders (`watchlist_updated(tenant_id, watchlist_id, name, symbols)`, `watchlist_deleted(tenant_id, watchlist_id)` — same `DomainEvent` envelope as existing builders).
- [ ] **Step 4: Run** — expect PASS.
- [ ] **Step 5: Write failing route tests** in `test_routes_watchlists.py` (httpx `AsyncClient` + fake session factory, same pattern as alert-service `test_routes.py`): GET list 200; GET by id 200/404; PUT 200 updates + 404 other-tenant; DELETE 204/404; all require `X-Tenant-Id` header (401 without).
- [ ] **Step 6: Run** — expect FAIL then implement thin routes (map `NotFoundError` → 404, `ValidationError` → 422) and re-run — PASS.
- [ ] **Step 7: Commit** `add watchlist crud to command service`

### Task 3: command-service alert rule delete

**Files:**
- Modify: `services/command-service/app/domain/events.py` (add `alert_rule_deleted(tenant_id, rule_id, symbol)`)
- Modify: `services/command-service/app/domain/service.py` (`delete_alert_rule(tenant_id: str, rule_id: str) -> None` — raises `NotFoundError`, sets `status="deleted"`, emits `alert_rule_deleted`)
- Modify: `services/command-service/app/api/routes.py` (`DELETE /v1/alert-rules/{id}` → 204 | 404)
- Test: `services/command-service/tests/test_command_service.py`, `services/command-service/tests/test_routes_watchlists.py`

**Interfaces:**
- Consumes: Task 2 repo port (`get_alert_rule`, `soft_delete_alert_rule`), Task 1 `ALERT_RULE_DELETED`.
- Produces: `DELETE /v1/alert-rules/{id}`; `alert_rule_deleted` event with data `{id, symbol}`.

- [ ] **Step 1: Failing tests** — service: delete sets status deleted + publishes event; unknown id raises `NotFoundError`. Route: 204 on own rule, 404 on unknown/other-tenant.
- [ ] **Step 2: Run** `test-command` — FAIL.
- [ ] **Step 3: Implement** — run again — PASS.
- [ ] **Step 4: Commit** `add alert rule delete to command service`

### Task 4: Demo tenant migration

**Files:**
- Create: `services/command-service/migrations/versions/0005_demo_tenant.py`

**Interfaces:**
- Produces: tenant row `id="11111111-2222-3333-4444-555555555555"`, `slug="demo"`, `name="Demo Tenant"`.

- [ ] **Step 1: Implement** — `upgrade()` inserts the fixed-UUID tenant row idempotently (check-then-insert or `op.execute` with `ON CONFLICT DO NOTHING`); `downgrade()` deletes exactly that id. Copy the table/column style from `0001_initial_schema.py`.
- [ ] **Step 2: Verify** `docker compose -f docker-compose.tests.yml run --rm test-command` still passes (models unchanged) and `python -c "import ast; ast.parse(open('services/command-service/migrations/versions/0005_demo_tenant.py').read())"` succeeds.
- [ ] **Step 3: Commit** `seed demo tenant in migration 0005`

### Task 5: alert-service trigger clear + deleted-rule consumer

**Files:**
- Modify: `services/alert-service/app/api/routes.py` (`DELETE /v1/triggers`)
- Modify: `services/alert-service/app/infra/consumer.py` (handle `alert_rule_deleted`)
- Test: `services/alert-service/tests/test_routes.py`, `services/alert-service/tests/test_alert_engine.py`

**Interfaces:**
- Consumes: Task 1 `ALERT_RULE_DELETED`.
- Produces: `DELETE /v1/triggers?acknowledged_only=true|false` → `{"deleted": <n>}` (200). Consumer: on `alert_rule_deleted`, `UPDATE alert_rules SET status='deleted' WHERE id=aggregate_id` (defensive consistency; evaluation already skips non-active rules).

- [ ] **Step 1: Failing route tests** — clear all deletes every seeded trigger row and returns count; `acknowledged_only=true` deletes only acknowledged rows; empty table returns `{"deleted": 0}`.
- [ ] **Step 2: Run** `docker compose -f docker-compose.tests.yml run --rm test-alert` — FAIL.
- [ ] **Step 3: Implement** the route (bulk `delete()` statement honoring the filter) — run — PASS.
- [ ] **Step 4: Failing consumer test** — engine `_process` with `event_type="alert_rule_deleted"` flips a seeded active rule's status to `deleted`; a subsequent candle event for that symbol does not fire a trigger.
- [ ] **Step 5: Run** — FAIL, implement handler in `_process` (new `elif` branch before the unknown-event fallback), run — PASS.
- [ ] **Step 6: Commit** `add trigger history clear and deleted rule handling to alert service`

### Task 6: gateway routes for new endpoints

**Files:**
- Modify: `services/api-gateway/internal/gateway/gateway.go` (route registrations only)
- Test: `services/api-gateway/internal/gateway/gateway_test.go`

**Interfaces:**
- Consumes: Task 2/3/5 upstream endpoints (command: watchlist CRUD + rule delete; alert: trigger clear).
- Produces (all wrapped `With(authMW, RateLimitMiddleware(limiter, logger))`):
  - `GET/PUT/DELETE /v1/watchlists` and `GET /v1/watchlists/*` → `g.proxyToCommand`
  - `DELETE /v1/alert-rules/*` → `g.proxyToCommand`
  - `DELETE /v1/triggers` → `g.proxyToAlert`

- [ ] **Step 1: Failing test** — table-driven: each new method+path routes to the correct upstream (assert via handler registration/behavior as existing tests do); request without auth in prod mode → 401; `X-Tenant-Id` forwarded.
- [ ] **Step 2: Run** `docker compose -f docker-compose.tests.yml run --rm test-gateway` — FAIL.
- [ ] **Step 3: Implement** — add the route lines following the existing `g.mux.With(...)` pattern — run — PASS.
- [ ] **Step 4: Commit** `route watchlist crud and trigger clear through gateway`

### Task 7: Frontend test infrastructure

**Files:**
- Modify: `frontend/package.json` (devDeps: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `jsdom`; scripts: `"test": "vitest run"`)
- Create: `frontend/vitest.config.ts` (jsdom environment, `@` alias optional — only if existing code uses one; globals off, setup file `src/test/setup.ts` importing `@testing-library/jest-dom`)
- Create: `frontend/src/test/setup.ts`
- Modify: `docker-compose.tests.yml` (new `test-frontend` service: `node:22-alpine`, working_dir `/app/frontend`, entrypoint `sh -c "npm ci && npx vitest run"`, volume `./frontend:/app/frontend`)
- Modify: `Makefile` (`test-frontend` target; add to `test:` aggregate line → `test: test-go test-python test-frontend`)

**Interfaces:**
- Produces: `npm test` inside `frontend/` runs vitest; `make test-frontend` works; `make test` includes it.

- [ ] **Step 1: Implement** config + compose + Makefile changes.
- [ ] **Step 2: Smoke test** — create `frontend/src/test/smoke.test.ts` (`expect(true).toBe(true)`); run `docker compose -f docker-compose.tests.yml run --rm test-frontend` — PASS.
- [ ] **Step 3: Commit** `add vitest test infrastructure for frontend`

### Task 8: Frontend OIDC + storage helpers

**Files:**
- Create: `frontend/src/auth/oidc.ts`
- Create: `frontend/src/auth/storage.ts`
- Test: `frontend/src/auth/oidc.test.ts`, `frontend/src/auth/storage.test.ts`

**Interfaces:**
- Produces (`oidc.ts`):
  - `createPkcePair(): Promise<{ verifier: string; challenge: string }>` — S256 (base64url(SHA-256(verifier)), no padding)
  - `buildAuthorizeUrl(cfg: OidcConfig, verifier: string, state: string, redirectUri: string): string` — query params: `client_id, response_type=code, scope=openid profile email, redirect_uri, state, code_challenge, code_challenge_method=S256`
  - `exchangeCode(cfg, code, verifier, redirectUri): Promise<TokenResponse>` and `refreshToken(cfg, refreshToken): Promise<TokenResponse>` — POST `{issuer}/token`, form-encoded, `TokenResponse = { access_token, refresh_token?, expires_in, id_token? }`
  - `decodeJwt(token: string): { sub?: string; preferred_username?: string; exp?: number; tenant_id?: string }` — payload-only decode
  - `OidcConfig = { issuer: string; clientId: string }`; defaults resolved in one exported `oidcConfigFromEnv(): OidcConfig` (`VITE_OIDC_ISSUER` default `/auth/realms/cryptoscope`, `VITE_OIDC_CLIENT_ID` default `cryptoscope-frontend`)
- Produces (`storage.ts`), keys prefixed `cryptoscope.auth.`:
  - `AuthSession = { accessToken: string; refreshToken: string | null; expiresAt: number; idToken: string | null; username: string | null }`
  - `loadSession(): AuthSession | null`, `saveSession(s: AuthSession): void`, `clearSession(): void`, `updateAccessToken(accessToken: string, expiresAt: number): void`

- [ ] **Step 1: Failing tests** — PKCE pair: verifier length ≥ 43, challenge = base64url(SHA-256(verifier)) computed in-test with node crypto; authorize URL contains all params with exact values; `decodeJwt` round-trips a hand-built token; storage round-trip/clear/update in jsdom.
- [ ] **Step 2: Run** `make test-frontend` — FAIL.
- [ ] **Step 3: Implement** both modules — run — PASS.
- [ ] **Step 4: Commit** `add oidc pkce helpers and token storage`

### Task 9: AuthContext, RequireAuth, Login, Callback, routes

**Files:**
- Create: `frontend/src/auth/AuthContext.tsx`
- Create: `frontend/src/auth/RequireAuth.tsx`
- Create: `frontend/src/pages/Login.tsx`
- Create: `frontend/src/pages/Callback.tsx`
- Modify: `frontend/src/main.tsx` (wrap routes in `AuthProvider`, add `/login` + `/callback` routes, wrap protected routes in `RequireAuth`)
- Test: `frontend/src/auth/AuthContext.test.tsx`, `frontend/src/pages/Login.test.tsx`, `frontend/src/pages/Callback.test.tsx`

**Interfaces:**
- Consumes: Task 8 helpers.
- Produces: `useAuth(): { user: { username: string | null }; token: string | null; status: "loading" | "authenticated" | "unauthenticated"; login(): void; loginDemo(): void; logout(): void }`; `AuthProvider` prop `children`. `login()` stores `state` (random) + verifier in sessionStorage (`cryptoscope.auth.oauth_state`, `.pkce_verifier`) and redirects to authorize URL with `redirect_uri = window.location.origin + "/callback"`. `loginDemo()` saves a session with username `demo` and exp 8 h (no network). `Callback` validates `state` param against stored value (mismatch → error UI), exchanges code, saves session, navigates to stored `state.from ?? "/"`. `RequireAuth` renders `<Navigate to="/login" state={{from: location}} replace />` when unauthenticated, spinner when loading.

- [ ] **Step 1: Failing tests** — AuthContext: restores valid session (authenticated); expired session with refresh token → calls `refreshToken` (mock `oidc.ts` via `vi.mock`) and stays authenticated; failed refresh → clears storage, status `unauthenticated` (Review Focus #1); `loginDemo` produces authenticated status. Login: renders Keycloak button; shows Demo button only when `import.meta.env.VITE_DEV_AUTH === "1"` (set via `vi.stubEnv`). Callback: state mismatch shows error; success navigates to `/`.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** all four files + `main.tsx` wiring — run — PASS.
- [ ] **Step 4: Commit** `add auth context routes and requireauth guard`

### Task 10: API client — auth headers, idempotency, new methods

**Files:**
- Modify: `frontend/src/api/client.ts`
- Test: `frontend/src/api/client.test.ts`

**Interfaces:**
- Consumes: Task 8 `loadSession`/`updateAccessToken`/`clearSession`, Task 2/3/5 endpoints.
- Produces: every request carries `Authorization: Bearer <accessToken>` when a session exists; every non-GET carries `Idempotency-Key: <uuid>` (crypto.randomUUID); on 401 with a refresh token → one refresh + retry; if that fails → `clearSession()` + redirect `/login`. New methods:
  - `listWatchlists(): Promise<Watchlist[]>` → GET `/v1/watchlists`
  - `getWatchlist(id): Promise<Watchlist>`
  - `updateWatchlist(id, name, symbols): Promise<Watchlist>` → PUT
  - `deleteWatchlist(id): Promise<void>` → DELETE
  - `deleteAlertRule(id): Promise<void>` → DELETE `/v1/alert-rules/{id}`
  - `clearTriggers(acknowledgedOnly: boolean): Promise<{ deleted: number }>` → DELETE `/v1/triggers?acknowledged_only=`

- [ ] **Step 1: Failing tests** (mock global fetch): Authorization + Idempotency-Key attached to POST; no Idempotency-Key on GET; 401 → refresh called → retried with new token → resolves; second 401 → clears session; new methods hit correct URL/method/body.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** — run — PASS. Also delete stray compiled `frontend/src/pages/*.js` artifacts and add `frontend/src/**/*.js` to `.gitignore` (they shadow imports).
- [ ] **Step 4: Commit** `send auth and idempotency headers from api client`

### Task 11: Watchlists page rewrite

**Files:**
- Modify: `frontend/src/pages/Watchlists.tsx` (full rewrite)
- Test: `frontend/src/pages/Watchlists.test.tsx`

**Interfaces:**
- Consumes: Task 10 client methods; `Watchlist` type from `src/types/index.ts`.
- Produces: page listing real watchlists (name, symbol chips, created date), create form (unchanged UX), per-card Edit (inline name + comma-separated symbols → `updateWatchlist`) and Delete (window.confirm → `deleteWatchlist`), error/success banners as today.

- [ ] **Step 1: Failing tests** (mock `../api/client`): renders fetched watchlists; create flow calls `createWatchlist` and reloads; edit flow calls `updateWatchlist` with edited values; delete calls `deleteWatchlist` after confirm; API error shows message.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** — run — PASS.
- [ ] **Step 4: Commit** `rewrite watchlists page on real crud endpoints`

### Task 12: AlertRules page — rules table + delete

**Files:**
- Modify: `frontend/src/pages/AlertRules.tsx` (add table + delete; creation form unchanged)
- Test: `frontend/src/pages/AlertRules.test.tsx`

**Interfaces:**
- Consumes: Task 10 `deleteAlertRule`; existing `listAlertRules`.
- Produces: table below the form with columns Symbol / Comparator / Threshold / Interval / Status / Created / actions; delete button per row (confirm) → `deleteAlertRule(id)` → reload.

- [ ] **Step 1: Failing tests** — renders fetched rules in table; delete calls `deleteAlertRule` after confirm and reloads; empty state text.
- [ ] **Step 2: Run** — FAIL → implement → PASS.
- [ ] **Step 3: Commit** `add alert rules table with delete`

### Task 13: AlertTriggers page — clear history

**Files:**
- Modify: `frontend/src/pages/AlertTriggers.tsx`
- Test: `frontend/src/pages/AlertTriggers.test.tsx`

**Interfaces:**
- Consumes: Task 10 `clearTriggers`.
- Produces: "Clear acknowledged" button (visible when unacked filter shows ≥1 acknowledged row) and "Clear all" (window.confirm) next to filter tabs; both reload after success.

- [ ] **Step 1: Failing tests** — clear acknowledged calls `clearTriggers(true)` and reloads; clear all requires confirm and calls `clearTriggers(false)`; buttons hidden when nothing to clear.
- [ ] **Step 2: Run** — FAIL → implement → PASS.
- [ ] **Step 3: Commit** `add trigger history clearing`

### Task 14: useCandleStream reconnect

**Files:**
- Modify: `frontend/src/hooks/useCandleStream.ts`
- Test: `frontend/src/hooks/useCandleStream.test.ts`

**Interfaces:**
- Produces: same signature, plus `{ candles, connected, reconnects: number }`. On `onerror`: close, schedule reconnect after `min(1000 * 2^attempt, 30000)` ms with jitter ±20%, increment `reconnects`, reset attempt on successful `connected` event. Cleanup cancels pending timers.

- [ ] **Step 1: Failing tests** (mock `EventSource` with a controllable fake class): error → reconnects after ~1 s with new EventSource; repeated failures grow delay capped at 30 s; successful connect resets backoff; unmount cancels pending reconnect.
- [ ] **Step 2: Run** — FAIL → implement → PASS.
- [ ] **Step 3: Commit** `add reconnect backoff to candle stream hook`

### Task 15: Layout — user menu + responsive drawer

**Files:**
- Modify: `frontend/src/components/Layout.tsx`
- Test: `frontend/src/components/Layout.test.tsx`

**Interfaces:**
- Consumes: Task 9 `useAuth`.
- Produces: header bar (mobile) with hamburger toggling the sidebar as an overlay drawer; user block at sidebar bottom showing username + Logout button (calls `logout()`); sidebar hidden below `lg` breakpoint, drawer visible when open.

- [ ] **Step 1: Failing tests** — shows username from `useAuth` mock; logout button calls `logout`; hamburger toggles drawer visibility.
- [ ] **Step 2: Run** — FAIL → implement → PASS.
- [ ] **Step 3: Commit** `add responsive layout and user menu`

### Task 16: Keycloak dev realm + compose + proxies

**Files:**
- Create: `deploy/keycloak/realm-export.json`
- Modify: `docker-compose.yml` (keycloak service, dev profile)
- Modify: `frontend/nginx.conf` (`/auth/` proxy)
- Modify: `frontend/vite.config.ts` (dev proxy `/auth` → `http://localhost:8081`)
- Modify: `.env.example` (Keycloak + frontend vars)
- Modify: `scripts/bootstrap.sh` (use the fixed demo tenant UUID header)

**Interfaces:**
- Consumes: Task 4 demo tenant UUID.
- Produces: realm `cryptoscope`; public client `cryptoscope-frontend` (standard flow, PKCE required); redirect URIs `http://localhost:5173/*`, `http://localhost:8080/*`; web origin `+`; demo user `demo@cryptoscope.local` with password from `KEYCLOAK_DEMO_PASSWORD` (compose default `demo-password`); client-scope mappers mapping `tenant_id` = `11111111-2222-3333-4444-555555555555` (hardcoded claim) and `tenant_slug` = `demo` into the access token. Compose service: `quay.io/keycloak/keycloak:26.0`, command `start-dev --import-realm`, env `KC_BOOTSTRAP_ADMIN_*`, volume `./deploy/keycloak:/opt/keycloak/data/import`, ports `8081:8080` (host 8081 → container 8080), profiles `["dev"]`. nginx (inside the compose network): `location /auth/ { proxy_pass http://keycloak:8080/auth/; }`. `docker-compose.prod.yml` gains the same keycloak service (internal port only, no host publishing). `scripts/bootstrap.sh` switches its `X-Tenant-Id` header from `demo-tenant` to the fixed demo UUID so seeding works against the UUID FK.

- [ ] **Step 1: Implement** all files (realm JSON validated with `python3 -m json.tool`).
- [ ] **Step 2: Verify** `docker compose -f docker-compose.yml config -q` parses; `npm run lint` (tsc) still clean.
- [ ] **Step 3: Commit** `add keycloak dev realm and auth proxy config`

### Task 17: Docs + roadmap + changelog

**Files:**
- Modify: `docs/roadmap.md` (Phase 5 all `[x]`; WebSocket item annotated `resolved by SSE streaming (useCandleStream auto-reconnect)`; success-criteria rows refreshed)
- Modify: `docs/CHANGELOG.md` (Unreleased: Added/Changed/Fixed — include the Idempotency-Key fix)
- Modify: `docs/API.md` (new endpoints + 401 semantics)
- Modify: `docs/DEPLOYMENT.md` (Keycloak service, `VITE_*` vars, realm import, `/auth/` proxy)
- Modify: `docs/security.md` (OIDC/PKCE flow, sessionStorage trade-off)
- Modify: `docs/guides/usage.md` (login + management walkthrough)
- Modify: `AGENTS.md` (test table: `make test-frontend`)

- [ ] **Step 1: Write** all doc updates (check off Phase 5 exactly as implemented; no invented features).
- [ ] **Step 2: Verify** `make lint` passes (go, python, frontend).
- [ ] **Step 3: Commit** `document phase 5 auth management uis and frontend tests`

### Task 18: Full verification

- [ ] **Step 1:** `make test` — all suites PASS.
- [ ] **Step 2:** `make lint` — clean.
- [ ] **Step 3:** Fix any failure found (amend or follow-up commit), re-run until green.
