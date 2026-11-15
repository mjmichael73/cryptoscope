# 8. Standardize observability on OpenTelemetry

Date: 2026-05-30

## Status

Accepted

Implementation note (November 15, 2026): current repository deployment files configure Fluent Bit to Loki and provision Grafana with Loki. Elasticsearch and Kibana are not included in the current stack. Instrumentation coverage and metric scraping should be checked service by service; this ADR records the intended direction, not verified completeness.

## Context

With six services and several data stores, a single request or event can touch
many hops. Debugging without correlated traces would be guesswork.

## Decision

Instrument services with OpenTelemetry. Export traces through an OTel
Collector to Jaeger, expose Prometheus metrics, and emit structured JSON logs.
The current checked-in log shipping configuration uses Fluent Bit and Loki,
with Grafana as the interface.

## Consequences

The goal is correlated traces, metrics, and logs. Coverage, propagation, and
scrape health remain operational checks rather than guaranteed properties of
the configuration files alone.
