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
