# 8. Standardize observability on OpenTelemetry

Date: 2026-05-30

## Status

Accepted

## Context

With six services and several data stores, a single request or event can touch
many hops. Debugging without correlated traces would be guesswork.

## Decision

Instrument every service with OpenTelemetry. Export traces through an OTel
Collector to Jaeger, expose Prometheus metrics, and emit structured JSON logs
that carry the trace and tenant identifiers. Logs ship to Elasticsearch and are
explored in Kibana.

## Consequences

We get correlated traces, metrics, and logs from day one. The cost is a shared
instrumentation library in each language, which we treat as first-class code.
