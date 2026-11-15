# API Reference — cryptoscope

All client-facing endpoints are served through the **api-gateway** at
`http://localhost:8080` (local dev). The gateway handles authentication, rate
limiting, and tenant resolution, then routes to the appropriate backend
service.

## Base URL

```
http://localhost:8080
```

## Authentication

In production, all `/v1/*` endpoints require a valid Keycloak JWT in the
`Authorization` header:

```
Authorization: Bearer <jwt-token>
```

In local dev (`DEV_MODE=true`), authentication is bypassed. The tenant is
resolved from the `X-Tenant-Id` header (or a default tenant if omitted).

## Rate limiting

All `/v1/*` endpoints are rate-limited per tenant using a Redis-backed token
bucket:

| Parameter               | Default | Description                   |
| ----------------------- | ------- | ----------------------------- |
| Requests per minute     | 120     | Sustained request rate        |
| Burst                   | 40      | Max burst above the sustained rate |

Exceeding the limit returns `429 Too Many Requests`.

---

## Health checks

### `GET /healthz`

Returns the gateway's own health status.

**Response** `200 OK`

```json
{
  "status": "ok"
}
```

### `GET /healthz/alert-service`

Proxied to the alert service's `/healthz` endpoint.

### `GET /healthz/command-service`

Proxied to the command service's `/healthz` endpoint.

---

## Query endpoints (read side)

The gateway calls the query service via gRPC on the backend.

### `GET /v1/candles`

Returns OHLCV candlestick data for a symbol and interval.

**Query parameters**

| Parameter  | Type   | Required | Default | Description                                  |
| ---------- | ------ | -------- | ------- | -------------------------------------------- |
| `symbol`   | string | yes      | —       | Trading pair (e.g. `BTCUSDT`, `ETHUSDT`)    |
| `interval` | string | no       | `1m`    | Candle interval: `1m`, `5m`, `1h`, `1d`     |
| `from_ms`  | int    | no       | 24h ago | Start time as Unix milliseconds             |
| `to_ms`    | int    | no       | now     | End time as Unix milliseconds               |

**Response** `200 OK`

```json
{
  "candles": [
    {
      "open_time_ms": 1692000000000,
      "open": 29000.50,
      "high": 29100.00,
      "low": 28950.25,
      "close": 29050.75,
      "volume": 125.34
    }
  ]
}
```

**Errors**

| Status | Body                                          | Cause                           |
| ------ | --------------------------------------------- | ------------------------------- |
| 400    | `{"error": "symbol is required"}`             | Missing `symbol` parameter      |
| 422    | `{"detail": "unsupported interval: ..."}`     | Invalid interval value          |
| 500    | `{"error": "query service error"}`            | Backend failure                 |

---

### `GET /v1/indicators`

Returns a computed technical indicator over a candle series.

**Query parameters**

| Parameter  | Type   | Required | Default | Description                                    |
| ---------- | ------ | -------- | ------- | ---------------------------------------------- |
| `symbol`   | string | yes      | —       | Trading pair                                   |
| `type`     | string | yes      | —       | Indicator type: `sma`, `ema`, `volatility`     |
| `interval` | string | no       | `1m`    | Candle interval to compute over                |
| `period`   | int    | no       | 14      | Lookback window size (must be ≥ 1)             |

**Supported indicator types**

| Type         | Description                                              |
| ------------ | -------------------------------------------------------- |
| `sma`        | Simple Moving Average of closing prices                  |
| `ema`        | Exponential Moving Average (seeded with SMA of first window) |
| `volatility` | Rolling standard deviation of closing prices             |

**Response** `200 OK`

```json
{
  "points": [
    {
      "time_ms": 1692000600000,
      "value": 29033.75
    }
  ]
}
```

**Errors**

| Status | Body                                                | Cause                              |
| ------ | --------------------------------------------------- | ---------------------------------- |
| 400    | `{"error": "symbol is required"}`                   | Missing `symbol`                   |
| 400    | `{"error": "type is required (sma, ema, volatility)"}` | Missing `type`                  |
| 422    | `{"detail": "unsupported indicator: ..."}`          | Unknown indicator type             |
| 500    | `{"error": "query service error"}`                  | Backend failure                    |

---

### `GET /v1/symbols`

Returns the list of symbols tracked for the current tenant.

**Response** `200 OK`

```json
{
  "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
}
```

---

## Command endpoints (write side)

The gateway reverse-proxies these to the command service. All write endpoints
require an `Idempotency-Key` header to prevent duplicate operations.

### `POST /v1/watchlists`

Creates a new watchlist for the current tenant.

**Headers**

| Header            | Required | Description                          |
| ----------------- | -------- | ------------------------------------ |
| `Idempotency-Key` | yes      | Unique key for idempotent execution  |

**Request body**

```json
{
  "name": "My Portfolio",
  "symbols": ["BTCUSDT", "ETHUSDT"]
}
```

| Field     | Type       | Required | Constraints        | Description        |
| --------- | ---------- | -------- | ------------------ | ------------------ |
| `name`    | string     | yes      | 1–128 characters   | Watchlist name     |
| `symbols` | string[]   | no       | —                  | List of symbols    |

**Response** `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Errors**

| Status | Body                        | Cause                             |
| ------ | --------------------------- | --------------------------------- |
| 409    | `{"detail": "..."}`         | Duplicate idempotency key         |
| 422    | `{"detail": "..."}`         | Validation error (e.g. empty name)|

---

### `POST /v1/alert-rules`

Creates a new price alert rule.

**Headers**

| Header            | Required | Description                          |
| ----------------- | -------- | ------------------------------------ |
| `Idempotency-Key` | yes      | Unique key for idempotent execution  |

**Request body**

```json
{
  "symbol": "BTCUSDT",
  "comparator": "crosses_above",
  "threshold": 30000.00,
  "interval": "1m",
  "window_seconds": null,
  "cooldown_seconds": 300
}
```

| Field             | Type   | Required | Default | Constraints                          | Description                               |
| ----------------- | ------ | -------- | ------- | ------------------------------------ | ----------------------------------------- |
| `symbol`          | string | yes      | —       | 1–32 characters                      | Trading pair to watch                     |
| `comparator`      | string | yes      | —       | see comparators below                | Trigger condition                         |
| `threshold`       | float  | yes      | —       | —                                    | Price level / percent / RSI threshold     |
| `interval`        | string | no       | `"1m"`  | `"1m"`, `"5m"`, `"1h"`               | Candle interval the rule is evaluated on  |
| `window_seconds`  | int    | no       | `null`  | 60–86400, `pct_change_*` only        | Lookback window for percent-change rules  |
| `cooldown_seconds`| int    | no       | `300`   | ≥ 1                                  | Min seconds between triggers of this rule |

**Comparators**

| Comparator          | Meaning                                                        |
| ------------------- | -------------------------------------------------------------- |
| `above`             | Close is above `threshold`                                     |
| `below`             | Close is below `threshold`                                     |
| `crosses_above`     | Previous close ≤ threshold and current close > threshold       |
| `crosses_below`     | Previous close ≥ threshold and current close < threshold       |
| `pct_change_above`  | Change over `window_seconds` is ≥ threshold (percent)          |
| `pct_change_below`  | Change over `window_seconds` is ≤ −threshold (percent)         |
| `rsi_above`         | RSI(14) is above `threshold`                                   |
| `rsi_below`         | RSI(14) is below `threshold`                                   |

**Response** `201 Created`

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001"
}
```

**Errors**

| Status | Body                        | Cause                             |
| ------ | --------------------------- | --------------------------------- |
| 409    | `{"detail": "..."}`         | Duplicate idempotency key         |
| 422    | `{"detail": "..."}`         | Invalid comparator, symbol, interval or window |

---

### `GET /v1/alert-templates`

Returns the catalog of alert rule templates (common patterns such as
"alert if BTC drops 5% in 1 hour"). The gateway reverse-proxies this to the
command service. Price-level templates leave `threshold` to the caller;
pattern templates pin `threshold` and `window_seconds`.

**Response** `200 OK`

```json
[
  {
    "id": "big-drop-1h",
    "name": "Big drop in 1 hour",
    "description": "Alert when the price loses 5% or more within an hour.",
    "comparator": "pct_change_below",
    "threshold": 5.0,
    "window_seconds": 3600,
    "interval": "1m",
    "cooldown_seconds": 900
  }
]
```

---

## Alert endpoints (read side)

The gateway reverse-proxies these to the alert service.

### `GET /v1/alert-rules`

Lists alert rules, optionally filtered by tenant.

**Query parameters**

| Parameter   | Type   | Required | Description                   |
| ----------- | ------ | -------- | ----------------------------- |
| `tenant_id` | string | no       | Filter by tenant              |

**Response** `200 OK`

```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "tenant_id": "demo-tenant",
    "symbol": "BTCUSDT",
    "comparator": "above",
    "threshold": 30000.00,
    "status": "active",
    "created_at": "2026-08-20T12:00:00Z",
    "updated_at": "2026-08-20T12:00:00Z",
    "interval": "1m",
    "window_seconds": null,
    "cooldown_seconds": 300
  }
]
```

---

### `GET /v1/alert-rules/{rule_id}`

Returns a single alert rule by ID.

**Path parameters**

| Parameter | Type   | Description       |
| --------- | ------ | ----------------- |
| `rule_id` | string | Alert rule UUID   |

**Response** `200 OK`

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "tenant_id": "demo-tenant",
  "symbol": "BTCUSDT",
  "comparator": "above",
  "threshold": 30000.00,
  "status": "active",
  "created_at": "2026-08-20T12:00:00Z",
  "updated_at": "2026-08-20T12:00:00Z",
  "interval": "1m",
  "window_seconds": null,
  "cooldown_seconds": 300
}
```

**Errors**

| Status | Body                        | Cause                   |
| ------ | --------------------------- | ----------------------- |
| 404    | `{"detail": "alert rule not found"}` | Rule does not exist |

---

### `GET /v1/triggers`

Lists alert trigger events, most recent first.

**Query parameters**

| Parameter   | Type   | Required | Default | Description                   |
| ----------- | ------ | -------- | ------- | ----------------------------- |
| `tenant_id` | string | no       | —       | Filter by tenant              |
| `limit`     | int    | no       | 50      | Max results to return         |

**Response** `200 OK`

```json
[
  {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "tenant_id": "demo-tenant",
    "rule_id": "660e8400-e29b-41d4-a716-446655440001",
    "symbol": "BTCUSDT",
    "comparator": "above",
    "threshold": 30000.00,
    "current_value": 30150.25,
    "triggered_at": "2026-08-20T14:30:00Z",
    "acknowledged": false,
    "interval": "1m",
    "window_seconds": null
  }
]
```

---

### `POST /v1/triggers/{trigger_id}/ack`

Marks a trigger as acknowledged. Acknowledging an already-acknowledged
trigger is a no-op. The gateway reverse-proxies this to the alert service.

**Path parameters**

| Parameter    | Type   | Description        |
| ------------ | ------ | ------------------ |
| `trigger_id` | string | Alert trigger UUID |

**Response** `200 OK` — the updated trigger object (same shape as
`GET /v1/triggers` items, with `"acknowledged": true`).

**Errors**

| Status | Body                              | Cause                    |
| ------ | --------------------------------- | ------------------------ |
| 404    | `{"detail": "trigger not found"}` | Trigger does not exist   |

---

## gRPC interface

The query service also exposes a gRPC API on port `9001` for internal service
communication (used by the api-gateway). The proto definitions are in
`proto/cryptoscope/v1/`.

### QueryService

| RPC              | Request                  | Response                 | Description            |
| ---------------- | ------------------------ | ------------------------ | ---------------------- |
| `GetCandles`     | `GetCandlesRequest`      | `GetCandlesResponse`     | Fetch OHLCV candles    |
| `GetIndicator`   | `GetIndicatorRequest`    | `GetIndicatorResponse`   | Compute an indicator   |
| `ListSymbols`    | `ListSymbolsRequest`     | `ListSymbolsResponse`    | List tracked symbols   |

### CommandService

| RPC                | Request                  | Response                 | Description            |
| ------------------ | ------------------------ | ------------------------ | ---------------------- |
| `CreateWatchlist`  | `CreateWatchlistRequest` | `CreateWatchlistResponse`| Create a watchlist     |
| `CreateAlertRule`  | `CreateAlertRuleRequest` | `CreateAlertRuleResponse`| Create an alert rule   |

See `proto/cryptoscope/v1/query.proto` and `proto/cryptoscope/v1/command.proto`
for the full message definitions.

---

## Common response format

All error responses use a consistent JSON shape:

```json
{
  "error": "human-readable message"
}
```

or for FastAPI validation errors:

```json
{
  "detail": "human-readable message"
}
```

## Frontend client

The frontend uses `frontend/src/api/client.ts` which calls all endpoints
through the gateway at `/api`. The Vite dev server proxies `/api` →
`http://localhost:8080`.
