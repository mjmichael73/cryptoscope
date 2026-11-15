# 4. Use CQRS for the read and write paths

Date: 2026-05-19

## Status

Accepted

Implementation note (November 15, 2026): the read/write service split exists, but the implementation is not a strict database-isolated CQRS design. `alert-service` reads command-service-owned `alert_rules` directly from shared PostgreSQL and writes trigger rows there; no separate event-projected read model is implemented. Domain events use the shared JSON envelope, while protobuf defines query/command gRPC contracts. See [current architecture](../architecture.md) and [roadmap](../roadmap.md).

## Context

The workload is read heavy and write light on the analytics side, but the
configuration side (tenants, watchlists, alert rules) needs strong consistency
on writes. Serving both from one model would force awkward compromises.

Concretely:

- **Reads**: clients fetch candle data, compute indicators, list symbols. These
  queries hit ClickHouse (analytics) and are served by `query-service`. They
  need to be fast, horizontally scalable, and free of contention from writes.
- **Writes**: clients create watchlists and alert rules. These mutate PostgreSQL
  rows and emit domain events. They need transactional consistency and
  idempotency.

The two workloads have different consistency requirements, different scaling
profiles, and different data store backends. A single service trying to do both
would have to juggle ClickHouse reads and PostgreSQL writes in the same request
path, coupling their lifecycle and making independent scaling impossible.

## Alternatives considered

### 1. Single service with shared database

One service handles all HTTP requests, reads from ClickHouse, and writes to
PostgreSQL directly.

**Rejected because**: couples the read and write lifecycles. A slow ClickHouse
query blocks the write path. Scaling reads requires scaling the whole service.
Adding new data stores (e.g., Redis caching) means modifying the same codebase.

### 2. CQRS with synchronous read model updates

Write to PostgreSQL, then synchronously update ClickHouse / read models before
returning the response.

**Rejected because**: adds latency to every write, couples the write path to
read store availability, and creates a distributed transaction problem. If
ClickHouse is down, writes fail — which is wrong for an analytics platform.

### 3. CQRS with event-driven eventual consistency (chosen)

Write to PostgreSQL, emit a domain event to Kafka, and let the read side
project events into its own stores asynchronously.

**Chosen because**: the write path is fast and independent. The read side can
lag slightly without affecting correctness (market data is already
append-only). Each side scales independently. The event backbone (Kafka)
provides durability, replay, and auditability.

## Decision

Separate the command and query responsibilities across dedicated services:

- **command-service** (Python/FastAPI) owns all mutable state: tenants,
  watchlists, and alert rules. It writes to PostgreSQL and emits domain events
  to the `domain.events` Kafka topic. Every write is idempotent via
  `Idempotency-Key`.

- **query-service** (Python/FastAPI) serves all read-only queries. It reads
  candles from ClickHouse, computes indicators (SMA, EMA, volatility), and
  lists tracked symbols. It is exposed via both REST and gRPC.

- **api-gateway** (Go) routes requests to the appropriate backend: gRPC to
  `query-service` for reads, HTTP reverse proxy to `command-service` for
  writes. It handles cross-cutting concerns (JWT auth, rate limiting, tenant
  resolution).

- **alert-service** (Python/FastAPI) consumes domain events from Kafka,
  evaluates alert rules against current prices, and writes triggers to
  PostgreSQL. It is decoupled from both the command and query paths.

The original design intended communication through Kafka rather than direct
database sharing. Current alert-service implementation is an exception: it
shares PostgreSQL and reads `alert_rules` directly. Treat that as an
implementation deviation from this decision, not as the intended service
boundary.

```
command-service ──write──► PostgreSQL
       │
       └──emit──► Kafka (domain.events) ──consume──► alert-service ──► PostgreSQL
                                    │
                                    └──consume──► (future read projections)

query-service ──read──► ClickHouse
       ▲
       │ gRPC / REST
       │
   api-gateway ◄── HTTP ── clients
```

## Consequences

### Positive

- **Independent scaling**: the read path (query-service) can scale horizontally
  behind a load balancer without touching the write path. ClickHouse handles
  high-throughput analytical queries. PostgreSQL handles transactional writes.

- **Independent evolution**: each service can change its data model, language,
  or deployment independently. The contract between them is the domain event
  schema on Kafka.

- **Fault isolation**: a ClickHouse outage degrades reads but does not block
  writes. A PostgreSQL outage degrades writes but does not block reads. The
  system degrades gracefully.

- **Auditability**: domain events on Kafka provide a durable, replayable log of
  every mutation. This is useful for debugging, reprocessing, and future read
  model projections.

### Negative

- **Eventual consistency**: a write to `command-service` is not immediately
  visible in `query-service`. The lag depends on Kafka consumer throughput and
  projection latency. For this domain (market analytics), a delay of seconds is
  acceptable — price data is already asynchronous.

- **Operational complexity**: running two Python services instead of one adds
  deployment and monitoring surface area. This is mitigated by the shared
  infrastructure (Docker Compose, OpenTelemetry, structured logging).

  - **Event schema evolution**: changing the domain event schema requires
  coordinating across producers and consumers. Kafka domain events currently
  use the shared JSON envelope; protobuf files define the gRPC service
  contracts.

### Risks

- **Projection lag**: if `alert-service` falls behind on consuming events,
  alerts may fire late. Mitigated by consumer group scaling and lag monitoring
  in Prometheus.

- **Duplicate events**: Kafka provides at-least-once delivery. Both
  `command-service` writes and `alert-service` evaluations use idempotency
  keys to handle duplicates safely.
