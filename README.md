# Cryptoscope

Cryptoscope is a multi-tenant cryptocurrency market analytics application. Go services poll Binance and Coinbase public REST APIs, publish normalized price ticks to Kafka, and aggregate them into candles. The API gateway exposes market queries, watchlists, alert rules, trigger history, and server-sent candle updates to a React client.

## System map

| Component | Stack | Responsibility |
| --- | --- | --- |
| `ingest-service` | Go | Poll Binance and Coinbase and publish deduplicated ticks |
| `stream-processor` | Go | Consume ticks, archive raw data in MongoDB, write candles to ClickHouse, and publish candle events |
| `query-service` | Python/FastAPI + gRPC | Read candles, indicators, symbol coverage, and exports from ClickHouse |
| `command-service` | Python/FastAPI | Own watchlists and alert-rule writes in PostgreSQL; publish domain events |
| `alert-service` | Python/FastAPI | Evaluate candle events against rules, persist triggers, and send configured notifications |
| `api-gateway` | Go | HTTP edge, JWT authentication, tenant propagation, rate limiting, backend proxying, and SSE |
| `frontend` | React, TypeScript, Vite | Dashboard, market views, watchlists, alert management, and trigger history |

Kafka topics default to `market.ticks.raw`, `domain.events`, and `alerts.triggers`. PostgreSQL stores command and alert records, ClickHouse stores candles, MongoDB archives raw ticks, and Redis backs rate limiting and ingestion deduplication.

## Run locally

Docker Compose is the supported development environment. Docker Compose v2 is required. The checkout has no `.env.example`, and the Compose file expects an existing external `shared-services-network`, a PostgreSQL service reachable there, and several required `.env` values. The stack is therefore not self-contained on a clean machine; see [deployment prerequisites](docs/DEPLOYMENT.md).

Before the commands below, provide `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`, `MONGO_ROOT_USERNAME`, `MONGO_ROOT_PASSWORD`, and `POSTGRES_DSN` in `.env`, and ensure the `shared-services-network` plus the shared PostgreSQL service exist. Then run:

```sh
make up                 # build and start the full stack, including the frontend
make ps
make logs
make seed               # seed the demo watchlist and alert rule
make down               # stop the stack and remove Compose-managed volumes
```

The UI is served at `http://localhost:5173`, the API gateway at `http://localhost:8080`, Grafana at `http://localhost:3000`, and Prometheus at `http://localhost:9090`. Keycloak is an opt-in Compose profile; start it with `docker compose --profile dev up -d keycloak` to make it available at `http://localhost:8081`. The realm includes `demo@cryptoscope.local`; its default password is `demo-password`. Change local credentials before sharing the environment.

`make up-all` starts backend containers and then runs the Vite development server on the host; it requires Node.js/npm in addition to Docker. `make seed` requires a running gateway and uses the local dev tenant headers. For API calls, the development gateway accepts `X-Tenant-Id` while `DEV_MODE=true`.

## Useful commands

```sh
make test              # Go, Python, and frontend suites
make lint              # Go, Python, and frontend checks
make proto             # regenerate Go and Python protobuf bindings
make migrate           # apply command-service Alembic migrations
make frontend          # production frontend build
```

The Makefile and [development guide](docs/guides/development.md) are the authoritative command references. Test and lint commands run in Docker Compose containers. They were not run as part of this documentation review.

## Documentation

- [Architecture](docs/architecture.md) and [ADRs](docs/adr/README.md)
- [API reference](docs/API.md) and [usage examples](docs/guides/usage.md)
- [Deployment](docs/DEPLOYMENT.md), [production notes](docs/production.md), and [security](docs/SECURITY.md)
- [Development](docs/guides/development.md), [testing](docs/testing.md), and [contributing](docs/CONTRIBUTING.md)
- [Roadmap and review findings](docs/roadmap.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md) and [changelog](docs/CHANGELOG.md)

## Known review findings

The current review found cross-tenant authorization gaps in alert-service routes, an ingestion dedupe ordering issue that can drop ticks after Kafka publish failures, broken production SSE scoping/authentication, a production CORS allowlist that omits `Idempotency-Key`, and an export route that ignores CSV requests. Details and priorities are tracked in [the roadmap](docs/roadmap.md). These issues have been documented, not fixed, in this documentation-only change.

## Repository layout

`proto/` contains service contracts; `services/` contains the six deployable application services and command-service Alembic migrations; `libs/` contains shared Go and Python packages; `frontend/` contains the SPA; `deploy/` contains Keycloak, observability, and Kubernetes manifests; root-level `docker-compose*.yml` files define Compose stacks; and `docs/` contains operational, API, contributor, and architecture documentation.

The project is licensed under the [MIT License](LICENSE).
