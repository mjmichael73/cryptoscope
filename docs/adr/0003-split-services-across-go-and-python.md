# 3. Split services by responsibility across Go and Python

Date: 2026-05-17

## Status

Accepted

## Context

Different parts of the system have different pressures. Ingestion and the
gateway are throughput and latency sensitive. The analytics and configuration
APIs benefit from a fast development loop and a rich data ecosystem.

## Decision

Use Go for `ingest-service`, `stream-processor`, and `api-gateway`, where
concurrency, low overhead, and predictable latency matter most. Use Python with
FastAPI for `query-service`, `command-service`, and `alert-service`, where
expressiveness and iteration speed help more.

## Consequences

The split is honest about each tool's strengths and shows I can lead a polyglot
codebase. It also means we maintain shared helpers in both languages, so we keep
those small and well tested.
