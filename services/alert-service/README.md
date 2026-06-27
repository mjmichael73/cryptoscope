# alert-service

Consumes domain events from Kafka, evaluates alert rules against incoming
candle data, and persists + publishes triggered alerts.

- Consumes from `domain.events` topic
- Evaluates active alert rules per tenant/symbol
- Persists `AlertTrigger` records to PostgreSQL
- Publishes triggers to `alerts.triggers` topic
- Exposes REST endpoints for querying rules and triggers
