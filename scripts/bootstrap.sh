#!/usr/bin/env bash
# Seed a demo tenant and a set of tracked symbols so the stack has data to work
# with right after startup. Safe to run more than once.
set -euo pipefail

API_GATEWAY="${API_GATEWAY:-http://localhost:8080}"

echo "==> Seeding demo tenant and watchlist via api-gateway"

# `docker compose up -d` returns before services have finished starting.
# Wait for the gateway and both seed endpoints; the gateway can be healthy
# while its command-service upstream is still starting.
wait_for_url() {
  local url="$1"
  for attempt in {1..60}; do
    if curl -fsS "$url" >/dev/null; then
      return 0
    fi
    if [[ "$attempt" -eq 60 ]]; then
      echo "service did not become ready at $url" >&2
      return 1
    fi
    sleep 2
  done
}

wait_for_url "$API_GATEWAY/healthz"
wait_for_url "$API_GATEWAY/healthz/command-service"
wait_for_url "$API_GATEWAY/healthz/alert-service"

# Create a demo watchlist
curl -fsS -X POST "$API_GATEWAY/v1/watchlists" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: 11111111-2222-3333-4444-555555555555" \
  -H "X-Tenant-Slug: demo" \
  -H "Idempotency-Key: bootstrap-watchlist-001" \
  -d '{"name": "Default Watchlist", "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]}' \
  | python3 -m json.tool

# Create an alert rule for BTC
curl -fsS -X POST "$API_GATEWAY/v1/alert-rules" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: 11111111-2222-3333-4444-555555555555" \
  -H "X-Tenant-Slug: demo" \
  -H "Idempotency-Key: bootstrap-alert-btc-001" \
  -d '{"symbol": "BTCUSDT", "comparator": "above", "threshold": 100000}' \
  | python3 -m json.tool

echo "==> Bootstrap complete"
