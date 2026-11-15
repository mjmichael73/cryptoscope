# Architecture

Cryptoscope separates market-data ingestion and analytics from client reads and user-managed configuration. The repository is a monorepo containing Go services, Python/FastAPI services, shared libraries, protobuf contracts, and a React SPA.

## Runtime flow

```text
Binance REST ─┐
              ├─ ingest-service ── market.ticks.raw ── stream-processor
Coinbase REST┘                                         ├─ MongoDB raw_ticks
                                                       ├─ ClickHouse candles
                                                       └─ domain.events
                                                            └─ alert-service
                                                               ├─ PostgreSQL triggers
                                                               └─ optional notifications

Browser ── HTTP/SSE ── api-gateway ──┬─ gRPC ── query-service ── ClickHouse
                                     ├─ HTTP ── command-service ── PostgreSQL
                                     └─ HTTP ── alert-service ──── PostgreSQL
```

The gateway is the client edge. In non-development mode it validates Keycloak RS256 JWTs, takes the tenant ID from the validated `tenant_id` claim, and forwards tenant headers to downstream services. Development mode bypasses JWT validation and supplies the fixed `demo-tenant` identity when none is provided; the demo UI uses a seeded demo tenant UUID through the local proxy. These development paths are not equivalent identity models.

## Service responsibilities

| Service | Inputs | Work and outputs |
| --- | --- | --- |
| `ingest-service` | Binance and Coinbase public REST polling | Normalizes current-price ticks, uses Redis dedupe, publishes to Kafka |
| `stream-processor` | Raw tick topic | Archives ticks in MongoDB, aggregates configured intervals, writes candles to ClickHouse, emits `candle_updated` events |
| `query-service` | REST and gRPC requests | Tenant-scoped candle, indicator, symbol-search, and export reads from ClickHouse |
| `command-service` | Gateway HTTP proxy | Tenant-scoped watchlist and alert-rule writes in PostgreSQL; publishes domain events |
| `alert-service` | Domain-event topic and PostgreSQL | Evaluates alert rules, stores trigger history, publishes alert events, dispatches configured notification channels |
| `api-gateway` | Browser HTTP/SSE | JWT checks, tenant propagation, Redis rate limiting, REST proxying, gRPC translation, SSE fanout |

The API gateway serves client REST and SSE; query-service also has its own HTTP and gRPC listeners for internal service communication. Backend listeners should be network-restricted.

## Storage and messaging

- **Kafka** carries `market.ticks.raw` and `domain.events`; `alerts.triggers` is the configured notification event topic.
- **ClickHouse** stores candle rows keyed by tenant, symbol, interval, and open time. The stream processor uses `ReplacingMergeTree` for repeated writes.
- **MongoDB** stores individual raw tick documents in `raw_ticks` for audit/replay use.
- **PostgreSQL** holds tenants, watchlists, alert rules, and alert triggers. Command-service migrations define the shared command tables.
- **Redis** stores gateway rate-limit state and short-lived ingestion dedupe keys.

## Contracts and shared code

`proto/cryptoscope/v1/` is the source for query and command gRPC contracts. Generated Go bindings are under `proto/cryptoscope/v1/`; Python bindings are under `libs/python/cryptoscope_proto/`. Shared Go modules are under `libs/go/`; shared Python code is under `libs/python/cryptoscope_shared/`.

## Observability

Services use shared structured logging, OpenTelemetry tracing, and Prometheus metrics where configured. The repository includes an OpenTelemetry Collector, Prometheus, Grafana dashboards, Loki configuration, and Fluent Bit shipping configuration. Verify each service's actual instrumentation and target configuration before relying on a dashboard; configuration presence alone does not prove metrics are scraped or traces exported.

## Important limitations

- Ingestion polls current-price endpoints rather than consuming exchange trade streams.
- Coinbase USD quotes are currently associated with USDT symbols, which can mix quote currencies in a candle series; see [roadmap findings](roadmap.md).
- Alert-service history for rolling conditions is held in process memory.
- Alert-service HTTP routes currently have tenant-isolation defects. Do not expose the application as a multi-tenant production system until the roadmap security findings are resolved.
- SSE is the implemented live update transport. There is no WebSocket endpoint.

See [ADRs](adr/README.md) for recorded design choices and [API](API.md) for current public routes.
