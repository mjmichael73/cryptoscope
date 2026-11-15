# 7. Make ingestion and commands idempotent

Date: 2026-05-27

## Status

Accepted

Implementation note (November 15, 2026): ingestion currently records the Redis dedupe key before publishing to Kafka. A publish failure can therefore suppress a retry until the key expires (24 hours in the service configuration). This violates the intended retry guarantee; see [roadmap](../roadmap.md).

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

This approach is intended to tolerate retries and redeliveries. Its current
ingestion ordering has a failure window between dedupe reservation and Kafka
publication, so it does not yet guarantee retry safety. Close that gap with a
pending/completed state or another durable publication protocol.
