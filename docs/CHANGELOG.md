# Changelog — cryptoscope

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
