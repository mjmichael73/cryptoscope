# cryptoscope

A multi-tenant crypto market analytics platform built as a polyglot
microservices system. cryptoscope ingests live market data from free, public
cryptocurrency APIs, streams it through Kafka, and turns it into queryable
time-series analytics and threshold alerts.

The project exists as a portfolio piece that shows how I approach backend work
at a senior/technical-lead level: clear service boundaries, CQRS, idempotent
ETL, observability, and a deployment story that runs locally with Docker
Compose and ships to Kubernetes in production.

## Why this project

Market data is a nice fit for a serious backend system. It is high volume,
append heavy, latency sensitive on reads, and it maps cleanly onto a
read/write split. That makes it a good stage for the patterns I wanted to
demonstrate without inventing artificial complexity.

All external data comes from public endpoints that need no API key:

- CoinGecko public API
- Binance public REST and WebSocket
- Coinbase Exchange public API

## Architecture at a glance

```
public APIs
    |
    v
ingest-service (Go) --> Kafka (market.ticks.raw)
                              |
                              v
                    stream-processor (Go)
                       |            |
                       v            v
                   MongoDB      ClickHouse (candles, analytics)
                                     ^
api-gateway (Go) <---- gRPC ---- query-service (Python, read side)
     |                                  ^
     | REST                             | read models
     v                                  |
  clients                          PostgreSQL
     |                                  ^
     | REST                             | write side
     v                                  |
command-service (Python) --> Kafka (domain.events) --> alert-service (Python)
```

A fuller breakdown lives in [docs/architecture.md](docs/architecture.md) and the decision
records in [docs/adr](docs/adr).

## Services

| Service            | Language        | Responsibility                                        |
| ------------------ | --------------- | ----------------------------------------------------- |
| `ingest-service`   | Go              | Pull and stream public market data, produce to Kafka  |
| `stream-processor` | Go              | ETL: raw archive to MongoDB, candles to ClickHouse    |
| `api-gateway`      | Go              | Edge REST, auth, tenant resolution, rate limiting     |
| `query-service`    | Python/FastAPI  | CQRS read side over ClickHouse and read models        |
| `command-service`  | Python/FastAPI  | CQRS write side, owns Postgres config, emits events   |
| `alert-service`    | Python/FastAPI  | Consumes events, evaluates alert rules                |

## Data stores

- **PostgreSQL** for tenants, watchlists, alert rules, and CQRS read models.
- **ClickHouse** for OHLC candles and time-series analytics.
- **MongoDB** for raw ingested payloads and an audit archive.
- **Redis** for rate limiting, idempotency keys, and hot-read caching.
- **Kafka** as the backbone for ticks, candles, domain events, and alerts.

## Cross-cutting concerns

- **Multitenancy** with a shared database and row-level tenant_id, resolved
  from Keycloak JWT claims.
- **Idempotency** on ingestion and commands, backed by Redis keys.
- **CQRS** with a clean write/read split across services.
- **Observability** through OpenTelemetry traces exported to Jaeger, Prometheus
  metrics, and Grafana dashboards.
- **Centralized logging** with structured JSON shipped to Elasticsearch and
  explored in Kibana.
- **Rate limiting** with a Redis token bucket at the gateway.

## Getting started

```bash
cp .env.example .env
make up          # start the full stack with Docker Compose
make bootstrap   # seed a demo tenant and tracked symbols
make test        # run the test suites
```

See [docs/guides/development.md](docs/guides/development.md) for local development
and [docs/guides/usage.md](docs/guides/usage.md) for API examples.
For production deployment, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Documentation

| Document                            | Description                                    |
| ----------------------------------- | ---------------------------------------------- |
| [docs/architecture.md](docs/architecture.md)       | System architecture, data flow, design decisions |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)           | Local and production deployment, env vars       |
| [docs/production.md](docs/production.md)           | Production deployment with K8s, scaling, backup |
| [docs/testing.md](docs/testing.md)                 | Test commands, conventions, how tests run        |
| [docs/security.md](docs/security.md)               | Security posture, auth, known dev-mode gaps     |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)       | How to contribute, code conventions, workflow    |
| [docs/roadmap.md](docs/roadmap.md)                 | Phased development roadmap                      |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and fixes                         |
| [docs/API.md](docs/API.md)                         | Full REST + gRPC API reference                   |
| [docs/guides/usage.md](docs/guides/usage.md)       | API usage guide with curl examples               |
| [docs/guides/development.md](docs/guides/development.md) | Local dev setup, workflows, project structure |
| [docs/CHANGELOG.md](docs/CHANGELOG.md)             | Version history                                 |
| [docs/adr/](docs/adr/)                             | Architecture decision records                   |

## Repository layout

```
proto/       gRPC and protobuf contracts shared across services
services/    the six microservices
libs/        shared Go and Python packages (config, logging, otel, kafka)
deploy/      Docker Compose, Kubernetes manifests, observability configs
migrations/  database migrations per owning service
docs/        architecture decision records, diagrams, and guides
frontend/    React + TypeScript SPA (Vite, Tailwind, Recharts)
```

## License

Released under the [MIT License](LICENSE).
