# Roadmap and review findings

Status reviewed on **November 15, 2026** against the checked-in source and deployment configuration. Checkboxes describe repository evidence, not production verification. No test suites or deployments were run for this review.

## Current capability

The repository contains application paths for polling Binance/Coinbase, producing Kafka ticks, creating interval candles, querying candle and symbol coverage, managing watchlists and alert rules, evaluating alert triggers, sending optional notifications, and presenting the data through a React SPA. The gateway supports Keycloak JWT validation, rate limiting, tenant propagation, and an SSE endpoint whose current implementation is incomplete. The local Compose file relies on external PostgreSQL/network setup and is not a self-contained stack.

Kubernetes and Swarm deployment definitions exist, but their presence does not establish a complete or secure production deployment. Kubernetes base manifests expect external infrastructure/secrets, the staging overlay enables auth bypass, and the Swarm file wires external services and secrets. Resolve the findings below before exposing a multi-tenant deployment.

## Prioritized confirmed bugs

These were found by static inspection. The documentation change records them; it does not change runtime code.

### P1 — Alert routes do not enforce tenant ownership

`services/alert-service/app/api/routes.py` accepts optional caller-supplied `tenant_id` filters for listing rules and triggers. The gateway forwards the authenticated tenant in headers, but the alert routes do not derive scope from that identity. `get_alert_rule`, `acknowledge_trigger`, and `clear_triggers` query or mutate records without tenant predicates. A caller with a valid account can supply another tenant ID to read its lists, fetch a rule by ID, acknowledge another tenant's trigger, or delete trigger history across tenants. The service routes are reachable through authenticated gateway paths, so gateway authentication alone does not prevent this.

**Resolution:** require a trusted tenant identity at the alert-service boundary (or an equivalent verified internal contract), remove caller-selected tenant filters from public routes, and include tenant ID in every select/update/delete predicate. Add cross-tenant route tests for list, detail, acknowledge, and clear operations.

### P1 — Failed Kafka publish can permanently suppress an ingested tick

`services/ingest-service/internal/pipeline/pipeline.go` calls `Deduper.FirstSeen` before publishing. `libs/go/idempotency/idempotency.go` commits the key immediately with `SETNX`; ingestion configures a 24-hour TTL. If Kafka publish fails, a later scheduler retry sees the key and skips the tick even though it was never published.

**Resolution:** make dedupe state represent successful publication, use a claim/complete or pending-state protocol, or use a transactional/outbox approach. Preserve concurrent duplicate protection and cover the publish-failure retry path.

### P1 — SSE does not serve the requesting tenant or market series

`services/api-gateway/internal/gateway/stream.go` polls ClickHouse with an empty tenant ID and hardcodes `BTCUSDT`; it does not read the authenticated tenant, requested symbol, or requested interval. The frontend opens the stream without query parameters and expects updates for its selected symbol and interval. In addition, browser `EventSource` cannot attach the Bearer token stored by the frontend, so the authenticated production gateway rejects the connection. The stream is therefore unusable for ordinary production sessions and does not match the client’s selected series.

**Resolution:** define a tenant-bound stream request contract, authorize it using a transport that supports credentials (or a short-lived stream token), query only the authenticated tenant and requested series, and cover reconnect and isolation behavior.

### P2 — Production browser writes fail CORS preflight

`services/api-gateway/internal/gateway/security.go` allows `Content-Type`, `Authorization`, and tenant headers, but omits `Idempotency-Key`. The frontend adds that header to every non-GET request in `frontend/src/api/client.ts`. A browser frontend on a separate allowed origin will preflight these requests and refuse to send them because the required header is not listed in `Access-Control-Allow-Headers`.

**Resolution:** allow `Idempotency-Key` and test preflight with the exact headers used by the frontend.

### P2 — Gateway candle export ignores the requested format

`services/api-gateway/internal/gateway/gateway.go` implements `/v1/candles/export` by fetching candles and returning JSON with a `format` field. It does not emit CSV or delegate to query-service's CSV implementation. A `format=csv` request therefore receives JSON.

**Resolution:** implement the gateway response serialization and content headers for both formats, or proxy to the query-service export route; test downloaded CSV and JSON responses.

## Other correctness and reliability work

- **P2 — Clean-checkout Compose startup is not self-contained.** `docker-compose.yml` requires `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`, `MONGO_ROOT_USERNAME`, `MONGO_ROOT_PASSWORD`, and `POSTGRES_DSN`, references an external `shared-services-network`, and assumes PostgreSQL is already running there. The repository has no `.env.example` and does not define a Postgres service in this Compose file. Either include PostgreSQL and an example local environment/network setup, or provision/document the shared dependency as an explicit prerequisite. Ensure first-run instructions work from a clean checkout.
- **P2 — Failed exchange fetches can look like empty successful batches.** `services/ingest-service/internal/source/coinbase.go` skips per-product errors and returns nil error; Binance may return a successful empty result when requested symbols are absent. Add structured per-source failure/coverage metrics and make empty or partial data visible to operators. Confirm desired retry policy.
- **P2 — Malformed tick messages are acknowledged after being dropped.** `services/stream-processor/internal/etl/etl.go` logs malformed JSON and returns nil, allowing the consumer to commit the message. Decide whether to quarantine to a dead-letter topic or intentionally discard with a counter and alert.
- **P2 — Coinbase USD prices are labeled as USDT symbols.** `toProduct` maps `BTCUSDT` to Coinbase `BTC-USD`, but the resulting USD price is published with the original `BTCUSDT` symbol and combined with Binance USDT prices. This mixes quote currencies in candle aggregation. Normalize symbols by quote currency, convert explicitly, or keep source-specific series.
- **P2 — Alert evaluation uses process-local price history.** `services/alert-service/app/infra/consumer.py` keeps rolling closes in `PriceHistory`; a restart loses prior samples required for percentage-change/window comparisons. Persist or reconstruct history, or document and surface the warm-up behavior.

## Delivery priorities

### 1. Tenant and request security

- [ ] Enforce tenant scope on every alert-service read and mutation, with cross-tenant regression coverage.
- [ ] Include `Idempotency-Key` in production CORS allow headers and validate browser preflight.
- [ ] Review internal service exposure and require authentication/network policy at the service boundary where traffic can bypass the gateway.
- [ ] Remove or clearly gate the staging `DEV_MODE=true` overlay before any shared or externally reachable staging environment.

### 2. Data integrity

- [ ] Correct ingestion dedupe ordering so publish failures remain retryable.
- [ ] Decide and implement dead-letter handling for malformed processor messages.
- [ ] Prevent mixed USD/USDT source values from entering the same candle series.
- [ ] Add explicit partial-source/empty-poll observability.
- [ ] Define restart behavior for alert windows and preserve required history.

### 3. Production operations

- [ ] Add load tests and publish measured API/streaming latency and throughput baselines.
- [ ] Define service-level indicators, objectives, alert thresholds, and operational runbooks.
- [ ] Verify backups and restore procedures for PostgreSQL, ClickHouse, MongoDB, Kafka, Redis, and observability state as applicable.
- [ ] Exercise broker, database, and downstream outage recovery and consumer replay behavior.
- [ ] Document supported production topology, required external infrastructure, and secret delivery for both Swarm and Kubernetes.

## Capability follow-ups

- [ ] Decide whether to add persistent market-source coverage/quality status.
- [ ] Revisit analytics breadth after data-series semantics are corrected.
- [ ] Keep SSE behavior and authentication documented as it evolves; no WebSocket endpoint is implemented.

## Targets and evidence

| Measure | Target | Current evidence |
| --- | --- | --- |
| Tenant data isolation | No cross-tenant reads or writes | Known alert-service authorization gaps listed above |
| API p95 latency | Establish target after load test | Not measured in this review |
| Availability objective | Define SLO and error budget | Not established |
| Tests | Meaningful tests for critical paths | Go, Python, and frontend test targets exist; not run for this review |
| Notifications | Multiple optional channels | SMTP, Slack, Telegram, and generic webhook implementations exist |
| Production deployment | Repeatable secure deploy and restore | Compose, Swarm, and Kustomize assets exist; integration and recovery not verified |
