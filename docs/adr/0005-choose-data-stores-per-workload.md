# 5. Choose data stores per workload

Date: 2026-05-21

## Status

Accepted

Implementation note (November 15, 2026): the ClickHouse table is currently ordered by `(tenant_id, symbol, interval, open_time)` and does not declare day partitioning. PostgreSQL is shared by command and alert services; MongoDB is written by stream-processor; Redis is used for rate limiting and ingest dedupe. See [current architecture](../architecture.md) for implemented ownership.

## Context

We have four distinct data shapes: append-heavy time series, relational
configuration, schema-flexible raw payloads, and ephemeral coordination state.
One store cannot serve all of them well.

## Decision

- ClickHouse for OHLC candles and analytics. The current table is ordered by
  `(tenant_id, symbol, interval, open_time)` and has no explicit partition key.
- PostgreSQL for tenants, watchlists, alert rules, and CQRS read models.
- MongoDB for raw ingested payloads and an audit archive.
- Redis for rate limiting and ingestion deduplication. The shared package also
  supports idempotency result storage; the current command path does not use a
  Redis result cache and the query service does not implement Redis hot-read
  caching.

PostgreSQL tables are shared directly by command-service and alert-service;
alert-service reads command-owned rule records and owns trigger history. Other
stores are accessed by their respective writer/read service paths.

## Consequences

Every workload gets a store that fits it. The cost is operational surface area,
which we manage with Docker Compose locally and Kubernetes manifests in
production.
