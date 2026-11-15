# Repository guide for contributors and coding agents

These instructions apply across the repository. Check for nested `AGENTS.md` files before changing a subdirectory; none were present during the November 15, 2026 documentation review.

## Project

Cryptoscope is a Go/Python market-data platform with a React frontend. Its six application services are `ingest-service`, `stream-processor`, `query-service`, `command-service`, `alert-service`, and `api-gateway`. The full local stack is defined in `docker-compose.yml`; test and lint runners are defined in `docker-compose.tests.yml`.

The source of truth for service contracts is `proto/cryptoscope/v1/`. Go modules are included in `go.work`; Python service packages live under `services/*/app` and shared Python code under `libs/python/cryptoscope_shared`.

## Before changing code

- Read the closest service README, relevant package code, and the related docs.
- Treat implementation and configuration as authoritative when they differ from prose; update the affected docs in the same change.
- Keep changes scoped. Do not commit unless the user asks.
- Do not claim tests, lint, deployment, or runtime behavior was verified unless you ran the corresponding command or inspected direct evidence.

## Commands

Docker Compose v2 is the expected environment. Common Make targets:

| Command | Effect |
| --- | --- |
| `make up` | Build and start the complete local stack |
| `make up-all` | Start backend containers and run Vite on the host |
| `make down` | Stop the stack and remove Compose volumes |
| `make ps`, `make logs`, `make restart svc=<service>` | Inspect or restart services |
| `make seed` | Seed the local demo watchlist and alert rule via the gateway |
| `make migrate` / `make migrate-new msg="..."` | Apply or create command-service Alembic migrations |
| `make proto` | Regenerate Go and Python protobuf bindings |
| `make test`, `make test-go`, `make test-python`, `make test-frontend` | Run test suites in containers |
| `make lint` | Run Go, Python, and frontend checks in containers |
| `make frontend` / `make frontend-dev` | Build or serve the frontend |
| `make k8s-build`, `make k8s-deploy`, `make k8s-status` | Build images or operate the Kustomize deployment |
| `make swarm-secrets`, `make swarm-deploy`, `make swarm-remove` | Prepare and operate the Swarm stack |

Use `make help` and the Makefile for the current complete target list. There is no `make bootstrap` target; the demo data command is `make seed`.

## Service boundaries and data flow

`ingest-service` polls Binance and Coinbase and publishes ticks to Kafka. `stream-processor` consumes those ticks, archives them to MongoDB, writes candles to ClickHouse, and publishes candle events. `query-service` exposes ClickHouse reads through REST and gRPC. `command-service` owns PostgreSQL writes for watchlists and alert rules. `alert-service` consumes domain events and writes trigger history to PostgreSQL. `api-gateway` authenticates and routes client HTTP/SSE traffic.

Redis is used by the gateway rate limiter and ingestion dedupe store. Notification implementations currently include SMTP email, Slack webhook, Telegram bot, and a generic webhook. Real-time candle delivery is SSE.

## Conventions

- Go: run `gofmt`; follow each module's existing package boundaries and `go.mod` replacement setup.
- Python: follow the service's `pyproject.toml`, Ruff, mypy, and async conventions.
- Frontend: TypeScript/React conventions in `frontend/`; use `npm run lint` and the existing Vitest setup when validation is requested.
- Keep tenant identity derived from a verified gateway JWT in non-development use and propagate it to every tenant-scoped store operation. Alert-service routes currently have known isolation gaps; see the roadmap before editing those routes.
- Keep credentials out of source control. Production settings use mounted secret files where supported; review `docs/production.md` because not all deployment secrets are wired uniformly.
- Preserve protobuf as the contract source and regenerate bindings with `make proto` after contract changes.
- Use structured logging through the shared packages. Avoid printing credentials or tokens.

## Scope and validation

Follow the user’s request for tests and verification. If requested, run the narrowest relevant Make target first, then broader checks as needed. The project’s test runner uses Docker and bind mounts. Do not commit unless explicitly requested.

## Documentation map

Start at `README.md`; current system behavior is described in `docs/architecture.md`, endpoints in `docs/API.md`, setup in `docs/DEPLOYMENT.md`, production constraints in `docs/production.md`, security in `docs/SECURITY.md`, and outstanding work in `docs/roadmap.md`. ADRs and dated superpowers plans/specs are historical design records; annotate them when they no longer match current implementation rather than silently treating them as current behavior.
