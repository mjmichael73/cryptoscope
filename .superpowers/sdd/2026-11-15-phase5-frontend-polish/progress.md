# SDD ledger — plan: docs/superpowers/plans/2026-11-15-phase5-frontend-polish.md

Setup: executing inline on `main` (repo convention: all history commits directly to main; user explicitly instructed "implement ... and then git commit"). No worktree.

Pre-flight scan (shared interfaces):
- Task 1 → 2,3,5: event constants WATCHLIST_UPDATED/WATCHLIST_DELETED/ALERT_RULE_DELETED — names pinned identically in producer and consumers. Clean.
- Task 2 → 3: repo port `get_alert_rule`/`soft_delete_alert_rule` — same names in Task 3 Consumes. Clean.
- Task 2/3/5 → 6: endpoint paths (GET/PUT/DELETE /v1/watchlists, GET /v1/watchlists/*, DELETE /v1/alert-rules/*, DELETE /v1/triggers) — identical strings. Clean.
- Task 2/3/5 → 10 → 11/12/13: client method names listWatchlists/getWatchlist/updateWatchlist/deleteWatchlist/deleteAlertRule/clearTriggers — consistent. Clean.
- Task 7 → 8-15: vitest infra; test files colocated `*.test.ts(x)`. Clean.
- Task 8 → 9,10: createPkcePair/buildAuthorizeUrl/exchangeCode/refreshToken/decodeJwt + loadSession/saveSession/clearSession/updateAccessToken — consistent. Clean.
- Task 9 → 15: useAuth shape {user, token, status, login, loginDemo, logout} — consistent. Clean.
- Task 4 → 16: demo tenant UUID 11111111-2222-3333-4444-555555555555 — same constant. Clean.
Task 1: complete (commits 042897c..HEAD, tests: docker compose test-libs-python → 45 passed)
Task 2: complete (commit "add watchlist crud to command service"; 67 tests pass, lint clean)
Ruling: route tests use real SQLAlchemy models on aiosqlite (added dev dep) instead of hand-rolled fake sessions — pins tenant-scoping against actual queries, matching the plan's intent.
Task 3: complete (commit "add alert rule delete to command service"; 72 tests pass)
Ruling: service-layer tests for rule delete passed on first run because Task 2's implementation already covered delete_alert_rule (shared port); route tests were still written first and failed before routes existed — RED confirmed at the route layer.
Task 5: complete (commit "add trigger history clear and deleted rule handling to alert service"; 88 alert-service tests pass; Python lint clean)
Ruling: alert-rule deletion is applied defensively by the consumer and candle evaluation also skips any non-active rule returned by its query. The latter guard makes the invariant explicit and protects against stale or inconsistent query results. RED was confirmed: the deletion consumer test first exposed a test fake returning an unawaited coroutine, then—after fixing the fake—showed that the fake does not apply SQL filters; the explicit status guard made the regression pass. Trigger deletion returns the SQL execution row count, with a typed-result-safe fallback.
Task 6: complete (commit "route watchlist crud and trigger clear through gateway"; gateway tests pass)
Ruling: management routes are registered with the same auth and rate-limit middleware chain as existing API routes. Reverse-proxy tests verify methods, paths, service destinations, and tenant header forwarding; production-mode requests without credentials receive 401. RED was confirmed by missing-route 404/405 responses before route registration.
Task 7: complete (commit "add vitest test infrastructure for frontend"; Docker frontend test runner passes smoke test)
Ruling: Vitest runs in jsdom with jest-dom matchers loaded from a shared setup file; `make test` now includes the Docker-backed `test-frontend` service. Host npm installation hit permissions in the existing `node_modules`, so dependencies and lockfile were installed from the Node Docker service as intended by the repository's Docker-only workflow.
Task 8: complete (commit "add oidc pkce helpers and token storage"; 9 frontend tests pass; TypeScript check clean)
Ruling: session state is stored as separate `cryptoscope.auth.*` entries in `sessionStorage`. `buildAuthorizeUrl` accepts the already-derived PKCE challenge as its second argument, because a synchronous URL builder cannot derive SHA-256 from a verifier without a sync crypto dependency; callers create the verifier/challenge pair asynchronously and retain the verifier for token exchange. Token requests use the explicit config issuer. RED was confirmed when tests could not resolve the not-yet-created OIDC/storage modules.
Task 9: complete (commit "add auth context routes and requireauth guard"; 18 frontend tests pass; TypeScript check clean)
Ruling: AuthProvider owns restore, refresh scheduling, local demo login, logout, and callback token acceptance. Callback state and verifier are kept in sessionStorage; the original route is saved separately as `return_to`, avoiding overloading OAuth's opaque state parameter. Refresh scheduling is re-created after every rotation so sessions continue refreshing. UI uses a responsive dark sign-in panel with labeled buttons, visible focus, and an explicit development-only demo action. RED was confirmed by missing context/guard/login/callback modules; initial implementation run also identified missing Testing Library cleanup and a callback test missing its provider, both corrected.
Task 10: complete (commit "send auth and idempotency headers from api client"; 23 frontend tests pass; TypeScript check clean)
Ruling: the client reuses the same Idempotency-Key across a 401 retry, persists refresh-token rotation, and emits `cryptoscope:auth-expired` so AuthProvider clears its in-memory session and RequireAuth returns the user to login. `exportCandles` also carries the bearer token. RED was confirmed by absent auth headers, failed 401 retry, missing management methods, and `.js` shadowing the TypeScript client; ignored generated source `.js` files were removed and the frontend ignore rule was made explicit.
Task 11: complete (commit "rewrite watchlists page on real crud endpoints"; 28 frontend tests pass; TypeScript check clean)
Ruling: watchlists now load from `listWatchlists`; create, inline edit, and confirmed delete all call the real client and reload persisted data. API failures render an alert, and empty lists show a clear create prompt. RED was confirmed across fetched data, create/reload, edit, delete, and error-state assertions against the old alert-rule-derived implementation.
Task 12: complete (commit "add alert rules table with delete"; 31 frontend tests pass; TypeScript check clean)
Ruling: rule creation remains intact; the existing rule list is presented as a responsive overflow table with the planned fields and a confirmed delete action that reloads after success. Empty-state text is retained. RED was confirmed because the prior div list had neither semantic table headers nor a delete action.
Task 13: complete (commit "add trigger history clearing"; 34 frontend tests pass; TypeScript check clean)
Ruling: clear actions are shown when their target set is non-empty: acknowledged history for `Clear acknowledged`, any history for `Clear all`. Clear-all requires confirmation; both actions reload history and report the returned deletion count. RED was confirmed for the two absent buttons while the empty-state visibility assertions already passed.
