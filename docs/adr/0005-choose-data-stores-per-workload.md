# 5. Choose data stores per workload

Date: 2026-05-21

## Status

Accepted

## Context

We have four distinct data shapes: append-heavy time series, relational
configuration, schema-flexible raw payloads, and ephemeral coordination state.
One store cannot serve all of them well.

## Decision

- ClickHouse for OHLC candles and analytics, partitioned by day and ordered by
  `(tenant_id, symbol, ts)`.
- PostgreSQL for tenants, watchlists, alert rules, and CQRS read models.
- MongoDB for raw ingested payloads and an audit archive.
- Redis for rate limiting, idempotency keys, and hot-read caching.

Each database has a single owning service. No service reaches into another
service's store.

## Consequences

Every workload gets a store that fits it. The cost is operational surface area,
which we manage with Docker Compose locally and Kubernetes manifests in
production.
