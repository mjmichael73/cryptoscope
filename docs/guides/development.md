# Local Development Guide — cryptoscope

Everything runs in Docker. The only host dependency is Docker itself.

## Quick start

```bash
git clone <repo-url> && cd cryptoscope
cp .env.example .env
make up          # start all services
make seed        # seed demo tenant + tracked symbols
```

Open `http://localhost:5173` for the frontend and `http://localhost:8080` for
the API gateway.

## What runs where

| Container          | Port  | What it does                                  |
| ------------------ | ----- | --------------------------------------------- |
| api-gateway        | 8080  | Edge API: auth, routing, rate limiting         |
| query-service      | 8001  | Read-side: candles, indicators, symbols        |
| command-service    | 8002  | Write-side: watchlists, alert rules            |
| alert-service      | 8003  | Alert evaluation engine                        |
| ingest-service     | —     | Polls Binance/Coinbase, publishes to Kafka     |
| stream-processor   | —     | Aggregates ticks into candles                  |
| frontend           | 5173  | React SPA (Vite dev server)                    |
| postgres           | 5432  | Tenants, watchlists, alert rules, triggers     |
| clickhouse         | 8123  | OHLC candles, time-series analytics            |
| mongo              | 27017 | Raw ingested payloads                          |
| redis              | 6379  | Rate limiting, idempotency keys                |
| kafka              | 9092  | Event backbone (ticks, domain events, alerts)  |
| prometheus         | 9090  | Metrics collection                             |
| grafana            | 3000  | Dashboards                                     |
| otel-collector     | 4317  | Trace collection                               |

## Development workflows

### Working on a Go service

```bash
# Run tests for the service you're editing
make test-gateway      # api-gateway
make test-ingest       # ingest-service
make test-processor    # stream-processor

# Open an interactive Go shell
make shell-go
cd services/api-gateway
go test ./... -v -run TestSpecificTest
```

Source is bind-mounted, so edits on the host are reflected immediately in the
test containers — no rebuild needed.

### Working on a Python service

```bash
# Run tests
make test-query        # query-service
make test-command      # command-service
make test-alert        # alert-service

# Open an interactive Python shell
make shell-python
cd /app
pytest tests/ -v
```

### Working on the frontend

```bash
# Start backend services only (no frontend container)
make up

# In another terminal, start the Vite dev server with hot-reload
make frontend-dev
# or: cd frontend && npm run dev
```

The Vite dev server proxies `/api` → `http://localhost:8080` so the frontend
talks to the gateway without CORS issues.

### Running linters

```bash
make lint              # all linters
make lint-go           # gofmt + go vet (Go services + libs)
make lint-python       # ruff + mypy (Python services + libs)
make lint-frontend     # tsc --noEmit (frontend TypeScript)
```

### Restarting a single service

```bash
make restart svc=api-gateway
make restart svc=query-service
make restart svc=command-service
```

### Viewing logs

```bash
make logs                          # tail all services
make logs 2>&1 | grep api-gateway  # filter to one service
docker compose logs -f api-gateway # direct docker compose
```

### Shell access into a running container

```bash
make shell svc=api-gateway
make shell svc=query-service
make shell svc=postgres
make shell svc=kafka
```

## Database management

### Running migrations

```bash
make migrate    # apply pending Alembic migrations
```

### Creating a new migration

```bash
make migrate-new msg="add alert_acknowledged column"
# Edit the generated file in migrations/command-service/
make migrate
```

### Querying databases directly

```bash
# PostgreSQL
make shell svc=postgres
psql -U cryptoscope -d cryptoscope

# ClickHouse
curl "http://localhost:8123/?query=SELECT+count()+FROM+candles"

# MongoDB
make shell svc=mongo
mongosh -u cryptoscope -p cryptoscope --authenticationDatabase admin

# Redis
make shell svc=redis
redis-cli
```

## Protobuf

Service contracts live in `proto/cryptoscope/v1/`. After editing `.proto`
files, regenerate stubs:

```bash
make proto
```

This regenerates both Go and Python stubs.

## Environment variables

All configuration is via environment variables. See `docker-compose.yml` for
the full set. Key variables:

| Variable                | Service(s)         | Description                       |
| ----------------------- | ------------------ | --------------------------------- |
| `DEV_MODE`              | api-gateway        | `true` bypasses JWT auth          |
| `LOG_LEVEL`             | all                | `debug`, `info`, `warn`, `error` |
| `KAFKA_BROKERS`         | Go services        | Comma-separated broker list       |
| `POSTGRES_DSN`          | command, alert     | PostgreSQL connection string      |
| `CLICKHOUSE_HOST`       | query-service      | ClickHouse host                   |
| `REDIS_ADDR`            | gateway, ingest    | Redis address                     |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | gateway | Per-tenant rate limit         |
| `INGEST_SYMBOLS`        | ingest-service     | Comma-separated symbol list       |
| `INGEST_POLL_INTERVAL_SECONDS` | ingest-service | Polling frequency            |

## Common issues

### Kafka not ready

If services fail to start because Kafka isn't ready, restart them:

```bash
make restart svc=ingest-service
make restart svc=stream-processor
```

Kafka health checks are configured, but timing issues can occur on first `make up`.

### Port conflicts

If a port is already in use:

```bash
lsof -i :8080   # find what's using it
kill <PID>      # stop it
make up         # try again
```

### Stale data

To start fresh:

```bash
make down       # stops containers and removes volumes
make up         # clean start
make seed       # re-seed demo data
```

### Test image rebuild

If Python tests fail with import errors after changing dependencies:

```bash
docker compose -f docker-compose.tests.yml build test-query
make test-query
```

## Project structure reference

```
services/<name>/
├── cmd/                    # Go: entrypoint (main.go)
├── internal/               # Go: private packages
│   ├── domain/             #   value types, events
│   ├── etl/                #   processing logic
│   ├── store/              #   persistence interfaces
│   └── config/             #   env-based config
├── app/                    # Python: FastAPI application
│   ├── main.py             #   app factory, lifespan
│   ├── settings.py         #   pydantic-settings config
│   ├── api/                #   routes, schemas, deps
│   ├── domain/             #   models, service, errors
│   └── infra/              #   repository, publisher, db
├── tests/                  # Python: pytest tests
├── go.mod                  # Go: module definition
├── pyproject.toml          # Python: project config
└── Dockerfile
```
