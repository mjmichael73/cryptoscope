# API usage guide

Examples target the local gateway at `http://localhost:8080`. With local `DEV_MODE=true`, supply the seeded tenant UUID for command-service operations:

```sh
export API=http://localhost:8080
export TENANT=11111111-2222-3333-4444-555555555555
```

In a non-development environment, obtain a valid Keycloak access token and use `Authorization: Bearer ...`; the gateway derives tenant identity from its verified `tenant_id` claim. Do not trust a client-supplied tenant query parameter for authorization.

## Health

```sh
curl "$API/healthz"
curl "$API/healthz/command-service"
curl "$API/healthz/alert-service"
```

The gateway `/healthz` reports gateway process health. Proxied health endpoints are simple service checks and may not verify every database dependency.

## Query market data

```sh
curl "$API/v1/symbols"
curl "$API/v1/symbols/search?q=BTC&limit=20"
curl "$API/v1/candles?symbol=BTCUSDT&interval=1m"
curl "$API/v1/indicators?symbol=BTCUSDT&type=sma&interval=1m&period=14"
```

`from_ms` and `to_ms` use Unix milliseconds. The candle gateway defaults to the last 24 hours. Available indicator calculations are implemented by query-service; see [API reference](../API.md).

## Create and manage a watchlist

```sh
curl -X POST "$API/v1/watchlists" \
  -H 'Content-Type: application/json' \
  -H "X-Tenant-Id: $TENANT" \
  -H 'Idempotency-Key: example-watchlist-001' \
  -d '{"name":"Core markets","symbols":["BTCUSDT","ETHUSDT"]}'

curl -H "X-Tenant-Id: $TENANT" "$API/v1/watchlists"
```

The frontend generates a fresh idempotency key for each non-GET request. Reuse a key only when retrying the same logical create operation.

## Create an alert rule

```sh
curl -X POST "$API/v1/alert-rules" \
  -H 'Content-Type: application/json' \
  -H "X-Tenant-Id: $TENANT" \
  -H 'Idempotency-Key: example-alert-001' \
  -d '{"symbol":"BTCUSDT","comparator":"above","threshold":100000,"interval":"1m","cooldown_seconds":300}'
```

Supported comparators are `above`, `below`, `crosses_above`, `crosses_below`, `pct_change_above`, `pct_change_below`, `rsi_above`, and `rsi_below`. Trigger evaluation depends on candle events and configured interval/window values.

## Alert history caution

The UI uses alert-service routes for rule and trigger history, acknowledgment, and clearing. Those routes currently lack consistent tenant enforcement. Do not use caller-provided `tenant_id` as a security boundary or expose these operations to multi-tenant users until the [P1 roadmap finding](../roadmap.md) is fixed.

## Export and live updates

`GET /v1/candles/export?symbol=BTCUSDT&format=csv` currently returns JSON with a `format` field, not a CSV download. The SSE endpoint also does not yet serve the requesting tenant/symbol and cannot use the frontend's Bearer token with the native `EventSource` flow. These paths are documented as current limitations in the [API reference](../API.md).
