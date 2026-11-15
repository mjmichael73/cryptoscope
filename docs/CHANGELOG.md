# Changelog — cryptoscope

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Technical indicators in the query service: MACD (line, signal, histogram) and Bollinger Bands (upper, middle, lower) join SMA, EMA and rolling volatility behind `GET /v1/indicators?type=...`; each multi-line indicator is exposed as its own `type` value
- RSI is now computed by the query service too, using the shared Wilder RSI moved into `cryptoscope_shared.indicators` (alert-service imports the same implementation)
- New indicator kinds selectable in the Market Data page

### Changed
- Alert-service RSI evaluation now imports Wilder's RSI from `cryptoscope_shared.indicators` instead of a local copy; behavior unchanged

## [0.2.0] — 2026-11-15

### Added
- Extended alert-rule comparators — crossing (`crosses_above`/`crosses_below`), percent change (`pct_change_above`/`pct_change_below`) and RSI(14) thresholds (`rsi_above`/`rsi_below`) — defined once in the shared `cryptoscope_shared.comparators` vocabulary module
- Telegram notification channel for alerts (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)
- Per-rule alert cooldown (`cooldown_seconds`, default 300s) that suppresses repeat triggers of a sustained condition
- Alert rule templates for common patterns ("big drop in 1 hour", "RSI overbought", ...) served by the command service at `GET /v1/alert-templates`
- Trigger acknowledgment: `POST /v1/triggers/{trigger_id}/ack` on the alert service, proxied through the gateway, with an All/Unacknowledged filter in the frontend trigger dashboard
- Alembic migration `0004_alert_rule_params`: `interval`, `window_seconds`, `cooldown_seconds` on `alert_rules`; `interval`, `window_seconds` on `alert_triggers`
- Comprehensive project documentation in `docs/`
- `docs/production.md` — production deployment guide
- `docs/architecture.md` — detailed system architecture with diagrams
- `docs/testing.md` — testing conventions and commands
- `docs/security.md` — security posture and hardening plan
- `docs/roadmap.md` — phased development roadmap
- `docs/contributing.md` — contribution guidelines
- `docs/deployment.md` — deployment and environment variable reference
- `docs/troubleshooting.md` — project-specific troubleshooting guide
- HorizontalPodAutoscalers for api-gateway, query-service and command-service in the production overlay
- Kubernetes manifests for the frontend, a Fluent Bit DaemonSet and a single-node Loki
- Fluent Bit → Loki log shipping: configs in `deploy/fluent-bit/` and `deploy/loki/`, auto-provisioned Grafana Loki datasource, opt-in `logs` profile for local Compose
- `docker-compose.prod.yml` — production stack for Docker Swarm, with `make swarm-deploy`, `swarm-secrets` and `swarm-remove`

### Changed
- Alert rules carry an `interval` (1m, 5m, 1h); the alert engine evaluates each rule only against candles of its own interval
- Percent-change comparators are evaluated over an in-memory rolling close history sized by `PRICE_HISTORY_MAXLEN` (default 480)
- Alert triggers record the interval and window that produced them, and notifications include that context
- Production overlay no longer pins static `replicas` for the HPA-managed services; the HPAs own the replica counts
- Dev compose reads `POSTGRES_DSN` from `.env` instead of embedding it
- Rewrote all existing docs to be project-specific instead of generic

## [0.1.0] — 2026-08-23

### Added
- **ingest-service** (Go): polls Binance and Coinbase public APIs, publishes raw ticks to Kafka
- **stream-processor** (Go): consumes ticks, aggregates OHLC candles, stores in ClickHouse and MongoDB
- **api-gateway** (Go): HTTP edge with JWT auth (Keycloak), rate limiting (Redis), routes to query/command/alert services
- **query-service** (Python/FastAPI): CQRS read side — candles, indicators, symbols via gRPC and REST
- **command-service** (Python/FastAPI): CQRS write side — watchlists, alert rules, emits domain events to Kafka
- **alert-service** (Python/FastAPI): consumes domain events, evaluates alert rules, stores triggers in PostgreSQL
- **frontend** (React/Vite/Tailwind): dashboard, market data charts, watchlists, alert rules, triggers
- Shared Go libraries: config, idempotency, kafka, logging, metrics, ratelimit, tenant, tracing
- Shared Python libraries: cryptoscope_shared (kafka, logging, settings, tenant, tracing), cryptoscope_proto
- Protobuf service contracts in `proto/cryptoscope/v1/`
- Docker Compose local dev stack (13 services)
- Test runner infrastructure via `docker-compose.tests.yml`
- Makefile with full developer command set
- OpenTelemetry tracing, Prometheus metrics, Grafana dashboards
- Architecture decision records in `docs/adr/`
- MIT License
