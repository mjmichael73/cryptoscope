# API Usage Guide — cryptoscope

This guide walks through every API endpoint with working `curl` examples.
The gateway runs at `http://localhost:8080` in local dev.

## Prerequisites

Start the stack and seed demo data:

```bash
make up
make seed
```

Wait a few seconds for the ingest service to start polling exchanges and
the stream processor to begin writing candles.

---

## Health checks

### Gateway health

```bash
curl http://localhost:8080/healthz
```

```json
{ "status": "ok" }
```

### Downstream health

```bash
curl http://localhost:8080/healthz/alert-service
curl http://localhost:8080/healthz/command-service
```

---

## Query endpoints (read side)

### List symbols

Returns all symbols currently tracked for the tenant.

```bash
curl http://localhost:8080/v1/symbols
```

```json
{
  "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
}
```

### Get candles

Fetch OHLCV candlestick data. Defaults to the last 24 hours of 1-minute candles.

```bash
# Default: last 24h of 1m candles for BTC
curl "http://localhost:8080/v1/candles?symbol=BTCUSDT"

# 1-hour candles
curl "http://localhost:8080/v1/candles?symbol=BTCUSDT&interval=1h"

# Custom time range (Unix milliseconds)
FROM_MS=$(($(date +%s) * 1000 - 3600000))  # 1 hour ago
TO_MS=$(($(date +%s) * 1000))              # now
curl "http://localhost:8080/v1/candles?symbol=BTCUSDT&interval=5m&from_ms=$FROM_MS&to_ms=$TO_MS"
```

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

**Supported intervals**: `1m`, `5m`, `1h`, `1d`

### Get indicators

Compute a technical indicator over a candle series.

```bash
# Simple Moving Average (period=14)
curl "http://localhost:8080/v1/indicators?symbol=BTCUSDT&type=sma&interval=1h&period=14"

# Exponential Moving Average
curl "http://localhost:8080/v1/indicators?symbol=BTCUSDT&type=ema&interval=1h&period=20"

# Rolling volatility (standard deviation)
curl "http://localhost:8080/v1/indicators?symbol=BTCUSDT&type=volatility&interval=1h&period=10"
```

```json
{
  "points": [
    { "time_ms": 1692000600000, "value": 29033.75 }
  ]
}
```

**Supported types**: `sma`, `ema`, `volatility`

---

## Command endpoints (write side)

All write endpoints require an `Idempotency-Key` header to prevent duplicate
operations. Use any unique string (UUID recommended).

### Create a watchlist

```bash
curl -X POST http://localhost:8080/v1/watchlists \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "name": "My Portfolio",
    "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
  }'
```

```json
{ "id": "550e8400-e29b-41d4-a716-446655440000" }
```

### Create an alert rule

Trigger an alert when a symbol crosses a price threshold.

```bash
# Alert when BTC goes above $30,000
curl -X POST http://localhost:8080/v1/alert-rules \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "symbol": "BTCUSDT",
    "comparator": "above",
    "threshold": 30000.00
  }'
```

```json
{ "id": "660e8400-e29b-41d4-a716-446655440001" }
```

**Comparators**: `"above"`, `"below"`

---

## Alert endpoints (read side)

### List alert rules

```bash
# All rules
curl http://localhost:8080/v1/alert-rules

# Filter by tenant
curl "http://localhost:8080/v1/alert-rules?tenant_id=demo-tenant"
```

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
    "updated_at": "2026-08-20T12:00:00Z"
  }
]
```

### Get a single alert rule

```bash
curl http://localhost:8080/v1/alert-rules/660e8400-e29b-41d4-a716-446655440001
```

### List alert triggers

```bash
# Recent triggers
curl http://localhost:8080/v1/triggers

# Limit results
curl "http://localhost:8080/v1/triggers?limit=10"

# Filter by tenant
curl "http://localhost:8080/v1/triggers?tenant_id=demo-tenant&limit=20"
```

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
    "acknowledged": false
  }
]
```

---

## Error responses

All errors return a JSON body with a description:

```bash
# Missing required parameter
curl "http://localhost:8080/v1/candles"
# 400: { "error": "symbol is required" }

# Duplicate idempotency key
KEY=$(uuidgen)
curl -X POST http://localhost:8080/v1/watchlists \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $KEY" \
  -d '{"name": "Test", "symbols": []}'
curl -X POST http://localhost:8080/v1/watchlists \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $KEY" \
  -d '{"name": "Test", "symbols": []}'
# 409: { "detail": "..." }

# Unsupported indicator type
curl "http://localhost:8080/v1/indicators?symbol=BTCUSDT&type=rsi&interval=1h&period=14"
# 422: { "detail": "unsupported indicator: rsi" }
```

---

## Using the frontend

The React frontend at `http://localhost:5173` provides a UI for all of the
above. Open it in your browser after `make up` to see live candlestick charts,
manage watchlists, create alert rules, and view triggers.

The frontend proxies `/api` to the gateway at `http://localhost:8080` via the
Vite dev server (configured in `frontend/vite.config.ts`).

---

## Using gRPC directly

The query service exposes a gRPC API on port `9001` for internal service
communication. You can test it with `grpcurl`:

```bash
# List available services
grpcurl -plaintext localhost:9001 list

# Get candles
grpcurl -plaintext -d '{
  "tenant_id": "demo-tenant",
  "symbol": "BTCUSDT",
  "interval": "INTERVAL_1H",
  "from_ms": 0,
  "to_ms": 9999999999999
}' localhost:9001 cryptoscope.v1.QueryService/GetCandles

# List symbols
grpcurl -plaintext -d '{
  "tenant_id": "demo-tenant"
}' localhost:9001 cryptoscope.v1.QueryService/ListSymbols
```
