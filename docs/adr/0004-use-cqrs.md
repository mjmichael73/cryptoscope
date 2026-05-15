# 4. Use CQRS for the read and write paths

Date: 2026-05-19

## Status

Accepted

## Context

The workload is read heavy and write light on the analytics side, but the
configuration side (tenants, watchlists, alert rules) needs strong consistency
on writes. Serving both from one model would force awkward compromises.

## Decision

Separate the command and query responsibilities. `command-service` owns writes
to PostgreSQL and emits domain events to Kafka. `query-service` serves reads
from ClickHouse for analytics and from denormalized read models for
configuration. The two sides communicate only through events, never by sharing
a database connection.

## Consequences

Each side scales and evolves on its own terms. We accept eventual consistency
between a write and its appearance in a read model, which is acceptable for this
domain and is made observable through tracing.
