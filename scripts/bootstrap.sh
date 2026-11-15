#!/usr/bin/env bash
# Seed a demo tenant and a set of tracked symbols so the stack has data to work
# with right after startup. Safe to run more than once.
set -euo pipefail

API_GATEWAY="${API_GATEWAY:-http://localhost:8080}"

echo "==> Seeding demo tenant and watchlist via api-gateway"

# Create a demo watchlist
curl -s -X POST "$API_GATEWAY/v1/watchlists" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: 11111111-2222-3333-4444-555555555555" \
  -H "X-Tenant-Slug: demo" \
  -H "Idempotency-Key: bootstrap-watchlist-001" \
  -d '{"name": "Default Watchlist", "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]}' \
  | python3 -m json.tool || echo "watchlist creation skipped (stack may be starting)"

# Create an alert rule for BTC
curl -s -X POST "$API_GATEWAY/v1/alert-rules" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: 11111111-2222-3333-4444-555555555555" \
  -H "X-Tenant-Slug: demo" \
  -H "Idempotency-Key: bootstrap-alert-btc-001" \
  -d '{"symbol": "BTCUSDT", "comparator": "gt", "threshold": 100000}' \
  | python3 -m json.tool || echo "alert rule creation skipped (stack may be starting)"

echo "==> Bootstrap complete"
