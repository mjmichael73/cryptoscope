# HTTP API

Client routes are exposed by `api-gateway` at `http://localhost:8080`. In Docker, the frontend nginx proxy exposes gateway paths under `/api/` and rewrites that prefix before forwarding.

## Authentication and tenant identity

When `DEV_MODE=false`, `/v1/*` routes require `Authorization: Bearer <Keycloak access token>`. The gateway validates RS256 signature, issuer, audience, expiration, and required `tenant_id` claim, then forwards tenant headers. When `DEV_MODE=true`, JWT checks are bypassed; local requests can provide `X-Tenant-Id` and otherwise use the gateway's `demo-tenant` fallback. The frontend local demo proxy uses the demo tenant UUID.

Do not use development identity behavior in a shared deployment. Alert-service routes currently have tenant authorization gaps described in [the roadmap](roadmap.md).

Create operations on watchlists and alert rules require `Idempotency-Key` at command-service. The frontend generates this header for non-GET requests. The production CORS middleware currently does not allow this header, so cross-origin browser writes fail preflight; same-origin frontend proxy requests are not subject to that restriction.

## Gateway health

| Method and path | Behavior |
| --- | --- |
| `GET /healthz` | Gateway process health response `{"status":"ok"}` |
| `GET /healthz/command-service` | Proxy to command-service `/healthz` |
| `GET /healthz/alert-service` | Proxy to alert-service `/healthz` |

These checks do not all verify datastore health. The gateway's own `/healthz` is not an upstream readiness check.

## Market data

All routes below require gateway authentication outside development mode.

| Method and path | Inputs | Success response |
| --- | --- | --- |
| `GET /v1/candles` | `symbol` required; `interval` defaults to `1m`; `from_ms`/`to_ms` Unix milliseconds default to the last 24 hours | `{"candles":[{ "open_time_ms", "open", "high", "low", "close", "volume" }]}` |
| `GET /v1/indicators` | `symbol`, `type` required; `interval` defaults to `1m`; `period` parsed as integer | `{"points":[{"time_ms","value"}]}` |
| `GET /v1/symbols` | — | `{"symbols":[...]}` |
| `GET /v1/symbols/search` | `q` optional (max 100 characters); `limit` optional (1–200, default 50) | `{"symbols":[{"symbol","first_open_time_ms","last_open_time_ms","candle_count","intervals"}]}` |
| `GET /v1/candles/export` | `symbol` required; `interval`, `from_ms`, `to_ms`, `format` optional | Currently returns JSON `{"candles":[...],"format":"..."}` for every requested format |
| `GET /v1/candles/stream` | SSE connection | `connected` and `candle` events; current implementation does not apply the requested symbol/interval/tenant and has production authentication limitations (see roadmap) |

Indicators accepted by query-service include `sma`, `ema`, `volatility`, `rsi`, `macd`, and `bollinger_bands`; behavior and parameters are implemented in `services/query-service/app/domain/indicators.py`. The gateway gRPC client surface passes only the indicator type and period, so do not assume all advanced indicator parameters are configurable through HTTP.

The gateway's export route currently labels a response with the requested `format` but serializes JSON. Query-service's internal HTTP route implements CSV and JSON, but the gateway does not proxy to it. Treat export as JSON until this is fixed.

## Watchlists and alert rules

Command-service routes are proxied by the gateway:

| Method and path | Purpose |
| --- | --- |
| `POST /v1/watchlists` | Create; requires `Idempotency-Key`; body `{ "name": string, "symbols": string[] }`; returns `201 {"id": string}` |
| `GET /v1/watchlists` | List tenant watchlists |
| `GET /v1/watchlists/{watchlist_id}` | Fetch a tenant watchlist |
| `PUT /v1/watchlists/{watchlist_id}` | Replace name and symbols |
| `DELETE /v1/watchlists/{watchlist_id}` | Delete a tenant watchlist; `204` on success |
| `POST /v1/alert-rules` | Create an alert rule; requires `Idempotency-Key`; returns `201 {"id": string}` |
| `DELETE /v1/alert-rules/{rule_id}` | Soft-delete an alert rule |
| `GET /v1/alert-templates` | List built-in rule templates |

Create alert-rule body fields: `symbol`, `comparator`, `threshold`; optional `interval` (`1m`, `5m`, `1h`, `1d`), `window_seconds` (60–86400), and `cooldown_seconds` (minimum 1, default 300). Comparators are `above`, `below`, `crosses_above`, `crosses_below`, `pct_change_above`, `pct_change_below`, `rsi_above`, and `rsi_below`.

Watchlist names must contain 1–128 characters. The response includes `id`, `tenant_id`, `name`, `symbols`, and `created_at`. Command-service is the owner of these writes.

## Alert rules and triggers

These paths are proxied to alert-service:

| Method and path | Purpose |
| --- | --- |
| `GET /v1/alert-rules` | List rules; current implementation accepts optional `tenant_id` query filter |
| `GET /v1/alert-rules/{rule_id}` | Fetch a rule by ID |
| `GET /v1/triggers` | List triggers; accepts optional `tenant_id` and `limit` (default 50) |
| `POST /v1/triggers/{trigger_id}/ack` | Mark a trigger acknowledged |
| `DELETE /v1/triggers?acknowledged_only=true` | Delete all triggers or acknowledged triggers only |

**Security note:** the current alert-service list/detail/mutation routes do not consistently enforce the authenticated tenant. Do not treat optional `tenant_id` as authorization. See the P1 roadmap issue and do not expose these paths in a multi-tenant deployment until fixed.

## Errors and rate limits

The gateway uses JSON `error` responses for its own validation and backend failures; FastAPI validation errors may use `detail`. Common statuses include `400` for gateway input checks, `401` for missing/invalid JWT, `404` for tenant-owned records not found in command-service, `409` for conflicts, `422` for FastAPI validation, `429` for rate limits, and `500` for backend failures. Exact mappings vary by route; consult the route implementation for edge cases.

The gateway applies a Redis-backed token bucket to `/v1/*`. Defaults are 120 requests per minute and burst 40. The limiter currently fails open if Redis errors or no limiter is supplied; production availability depends on Redis configuration.

## Internal APIs

Query-service exposes internal FastAPI routes matching candle, indicator, symbol, and export operations, and a gRPC `QueryService` defined in `proto/cryptoscope/v1/query.proto`. Keep these internal listeners inaccessible to untrusted clients. Generated contracts are not edited directly; regenerate with `make proto`.
