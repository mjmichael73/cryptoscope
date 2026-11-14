# Contributor notes

These notes help anyone working in this repository move quickly and keep the
codebase consistent. They apply to the whole tree unless a nested file says
otherwise.

## Project overview

cryptoscope is a polyglot crypto market analytics platform. Price data flows from
public exchange APIs through an ingest pipeline, is aggregated into candlesticks
by a stream processor, and served to clients through a gateway that proxies both
REST queries and write commands.

The entire dev environment runs in Docker. The only host dependency is Docker
itself.

## Repository layout

```
├── proto/                         # gRPC protobuf definitions (source of truth)
│   └── cryptoscope/v1/            #   service and message definitions
├── libs/
│   ├── go/                        # Go shared packages (8 sub-modules)
│   │   ├── config/                #   env-based config loader
│   │   ├── idempotency/           #   Redis-backed idempotency store
│   │   ├── kafka/                 #   Kafka producer/consumer wrappers
│   │   ├── logging/               #   structured JSON logging (slog)
│   │   ├── metrics/               #   Prometheus HTTP metrics server
│   │   ├── ratelimit/             #   Redis token-bucket rate limiter
│   │   ├── tenant/                #   tenant identity context helpers
│   │   └── tracing/               #   OpenTelemetry tracing setup
│   └── python/                    # Python shared packages
│       ├── cryptoscope_shared/    #   kafka, logging, settings, tenant, tracing
│       └── cryptoscope_proto/     #   generated protobuf stubs
├── services/
│   ├── ingest-service/            # Go — polls Binance, Coinbase; publishes ticks to Kafka
│   ├── stream-processor/          # Go — consumes ticks, aggregates candles, stores in ClickHouse + Mongo
│   ├── api-gateway/               # Go — HTTP→gRPC gateway, JWT auth, rate limiting, reverse proxy
│   ├── command-service/           # Python/FastAPI — write-side: watchlists, alert rules → Kafka events
│   ├── query-service/             # Python/FastAPI — read-side: candles, indicators, symbols
│   └── alert-service/             # Python/FastAPI — consumes events, evaluates rules, emits triggers
├── frontend/                      # React + TypeScript SPA (Vite, Tailwind, Recharts)
│   ├── src/
│   │   ├── api/client.ts          #   REST client for all backend endpoints
│   │   ├── components/            #   Layout, CandleChart, IndicatorChart
│   │   ├── pages/                 #   Dashboard, MarketData, Watchlists, AlertRules, Triggers, Health
│   │   └── types/index.ts         #   shared TypeScript interfaces
│   └── Dockerfile                 #   nginx production image
├── migrations/
│   └── command-service/           # Alembic migrations for the command service
├── scripts/
│   ├── bootstrap.sh               # seed demo tenant + watchlist
│   └── gen_proto.sh               # protobuf stub generator
├── deploy/                        # observability + deployment configs
│   ├── fluent-bit/                #   Fluent Bit → Loki log shipping config
│   ├── grafana-dashboards/
│   ├── loki/                      #   Loki single-binary config
│   ├── otel-collector.yaml
│   └── prometheus.yaml
├── docker-compose.yml             # full dev stack (13 services incl. data stores)
├── docker-compose.prod.yml        # production stack for Docker Swarm (app tier + observability)
├── docker-compose.tests.yml       # test/lint/proto runner services
├── Dockerfile.proto               # protobuf toolchain image
├── Dockerfile.test.python         # Python test image with dev deps
├── Makefile                       # all developer commands
├── go.work                        # Go workspace
├── AGENTS.md                      # this file
└── docs/
    ├── architecture.md            # system architecture, data flow, design decisions
    ├── DEPLOYMENT.md              # local and production deployment, env vars
    ├── production.md              # production deployment with K8s, scaling, backup
    ├── testing.md                 # test commands, conventions, how tests run
    ├── SECURITY.md                # security posture, auth, known dev-mode gaps
    ├── CONTRIBUTING.md            # how to contribute, code conventions, workflow
    ├── roadmap.md                 # phased development roadmap
    ├── TROUBLESHOOTING.md         # common issues and fixes
    ├── CHANGELOG.md               # version history
    └── adr/                       # architecture decision records
```

## Documentation

Detailed docs live in `docs/`:

- **docs/architecture.md** — full system diagram, service responsibilities, data stores, design decisions
- **docs/DEPLOYMENT.md** — local dev setup, env vars, service ports
- **docs/production.md** — production deployment, K8s manifests, scaling, backup
- **docs/testing.md** — test commands, conventions, writing new tests
- **docs/security.md** — auth, multi-tenancy, rate limiting, known issues
- **docs/CONTRIBUTING.md** — contribution workflow and code conventions
- **docs/roadmap.md** — phased development roadmap
- **docs/TROUBLESHOOTING.md** — common issues and fixes
- **docs/API.md** — full REST and gRPC API reference
- **docs/guides/usage.md** — API usage guide with curl examples
- **docs/guides/development.md** — local dev setup, workflows, project structure
- **docs/CHANGELOG.md** — version history
- **docs/adr/** — architecture decision records

## Architecture

```
Exchange APIs (Binance, Coinbase)
        │
        ▼
  ingest-service (Go) ──► Kafka (market.ticks.raw)
        │
        ▼
  stream-processor (Go) ──► ClickHouse (candles)
                          ──► Mongo   (latest state)
        │
        ├── query-service (Python) ◄── gRPC ── api-gateway (Go) ◄── HTTP ── Client
        │                                              │
        └── command-service (Python) ◄── HTTP ─────────┘
                 │
                 └──► Kafka (domain.events) ──► alert-service (Python)
                                                      │
                                                      └──► PostgreSQL (alert_triggers)
```

See `docs/architecture.md` for the full breakdown.

## All Makefile commands

### Stack lifecycle
| Command | Description |
|---------|-------------|
| `make up` | Start all services (backend + frontend via Docker) |
| `make up-all` | Start backend Docker services + frontend dev server with hot-reload |
| `make down` | Stop stack and remove volumes |
| `make build` | Build all Docker images without starting |
| `make restart svc=<name>` | Restart a single service |
| `make ps` | List running services |
| `make logs` | Tail logs from all services |
| `make clean` | Remove all containers, volumes, and build cache |
| `make swarm-secrets` | Create Docker secrets from `./secrets/` files (idempotent) |
| `make swarm-deploy` | Deploy the production stack to a Swarm manager |
| `make swarm-remove` | Remove the Swarm stack |

### Shell access
| Command | Description |
|---------|-------------|
| `make shell svc=<name>` | Open shell in a running service container |
| `make shell-go` | Interactive Go dev shell with source mounted |
| `make shell-python` | Interactive Python dev shell with source mounted |

### Database
| Command | Description |
|---------|-------------|
| `make migrate` | Run pending Alembic migrations |
| `make migrate-new msg="description"` | Create a new autogenerated migration |
| `make seed` | Seed demo tenant + tracked symbols |

### Protobuf
| Command | Description |
|---------|-------------|
| `make proto` | Regenerate Go and Python stubs from proto/ |

### Frontend
| Command | Description |
|---------|-------------|
| `make frontend` | Build the React frontend for production |
| `make frontend-dev` | Start Vite dev server on the host |

### Testing
| Command | Description |
|---------|-------------|
| `make test` | Run **all** Go + Python tests (what you want) |
| `make test-go` | All Go tests (3 services + 8 libs) |
| `make test-python` | All Python tests (3 services + libs) |
| `make test-ingest` | Single service: ingest-service |
| `make test-processor` | Single service: stream-processor |
| `make test-gateway` | Single service: api-gateway |
| `make test-command` | Single service: command-service |
| `make test-query` | Single service: query-service |
| `make test-alert` | Single service: alert-service |
| `make test-libs-go` | All Go shared library tests |
| `make test-libs-python` | All Python shared library tests |

### Linting
| Command | Description |
|---------|-------------|
| `make lint` | Run all Go + Python + frontend linters |
| `make lint-go` | gofmt + go vet on all Go code |
| `make lint-python` | ruff + mypy on all Python code |
| `make lint-frontend` | TypeScript type check on frontend code |

## How tests work

All commands in the Makefile route through `docker-compose.tests.yml`. Source
code is mounted as a bind volume — edit on the host, re-run the test, no image
rebuild needed.

```bash
# Under the hood, `make test-ingest` runs:
docker compose -f docker-compose.tests.yml run --rm test-ingest
```

### Go tests
Run inside `golang:1.25-alpine` containers. Each service module is independent
(go.mod with replace directives). The `test-libs-go` service iterates over all
8 library sub-modules.

### Python tests
Run inside pre-built images that cache `pip install ".[dev]"`. Building images
happens once, then test containers start in ~0.1s.

```
make build   # builds production images
# Test images built automatically on first `make test-*`
```

### Frontend tests / lint
The frontend TypeScript type check runs inside `node:22-alpine`:
```
make lint-frontend
```

## Code conventions

### Go
- Format: `gofmt` (enforced by `make lint-go`)
- Standard project layout per module (cmd/, internal/)
- Dependencies use `go.mod` replace directives for local libs
- `go vet ./...` must pass (enforced by `make lint-go`)

### Python
- Format: `ruff` (enforced by `make lint-python`)
- Type checks: `mypy` must pass (enforced by `make lint-python`)
- All services use `pyproject.toml` with `hatchling` build backend
- FastAPI apps use `src` package layout (`app/` directory)
- Tests go in a `tests/` directory at the service root
- Async test fixtures use `@pytest.fixture` and `async def`
- All test files are prefixed `test_`

### Testing conventions
- Write the test alongside the behavior it covers
- Prefer in-memory fakes over mocks for Go interfaces
- Python tests use pytest with `asyncio_mode = "auto"`
- Every domain error should have a corresponding test
- Table-driven tests for parsing/enum logic

### Logging
- Log in structured JSON. Do not use plain print statements.
- Go: use `slog` with `logging.New(service, level)`
- Python: use `structlog` with `configure_logging(service, level)`
- Every log line carries `service`, `tenant_id`, and `trace_id` when available

### Other
- Every tenant-scoped query must filter by `tenant_id`
- Keep changes feature scoped and commit them that way
- Prefer extending shared libs over copying helpers between services
- Protobuf is the source of truth for service contracts

## Git conventions

- Author: `Mojtaba Michael <mojimich2015@gmail.com>`
- Commits span 2026-05-15 → present with natural spacing
- Use the helper for backdated commits:
  ```bash
  GIT_AUTHOR_DATE="$when" GIT_COMMITTER_DATE="$when" git commit -q -m "$message"
  ```
  where `$when` is a format like `"2026-06-01 14:30:00 +0000"`
- Commit messages are concise, lowercase, no trailing period
- Do not commit unless asked

## Common workflows

### Add a new Go library
1. Create `libs/go/<name>/` with `go.mod` and source
2. Update `docker-compose.tests.yml` — add module to `test-libs-go` loop
3. Update `Makefile` — add to `GO_SERVICE_NAMES` if it's a service

### Add a new Python library
1. Add code under `libs/python/cryptoscope_shared/`
2. Add tests in `libs/python/tests/`
3. Regenerate proto stubs if needed: `make proto`

### Add a database migration
```bash
make migrate-new msg="add alert_acknowledged column"
# Edit the generated file in migrations/command-service/
make migrate
```

### Debug a single service
```bash
make up              # start everything
make logs            # tail all logs
make shell svc=<name>  # dive into a container
# Or run just its tests in isolation:
make test-command    # e.g. for command-service
```

### Full iteration loop
```bash
# 1. Edit code on the host
# 2. Run relevant tests (no rebuild needed):
make test-gateway
# 3. Restart the service with new code:
make restart svc=api-gateway
# 4. Check logs:
make logs
```
