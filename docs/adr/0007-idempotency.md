# 7. Make ingestion and commands idempotent

Date: 2026-05-27

## Status

Accepted

## Context

At-least-once delivery is the realistic guarantee for our HTTP polling and
Kafka consumers. Without care, retries would create duplicate ticks, duplicate
candles, and duplicate command effects.

## Decision

Give every ingested tick a deterministic key derived from source, symbol, and
timestamp, and deduplicate on it in Redis. Require an idempotency key on write
commands and store the result so a replay returns the original outcome.
ClickHouse and PostgreSQL writes use upserts so a retry converges rather than
duplicates.

## Consequences

The system tolerates retries and redeliveries without corrupting data. The cost
is a Redis lookup on the hot path, which is cheap relative to the safety it
buys.
