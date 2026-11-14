# Roadmap — cryptoscope

## Current state

The platform has a working end-to-end pipeline: exchange data flows through Kafka, is aggregated into candles, stored in ClickHouse, and served through the API gateway. The command side supports watchlists and alert rules. The frontend is a functional SPA.

**Working**: ingestion, stream processing, candle storage, query API, command API, alert evaluation, frontend dashboard

**Needs work**: security hardening, production readiness, expanded analytics, operational maturity

---

## Phase 1 — Security hardening 🔴

Priority: critical. The dev stack bypasses authentication and uses hardcoded credentials.

- [x] Disable `DEV_MODE` in production and complete Keycloak JWT validation
- [x] Move all database credentials to a secrets manager (Vault or cloud)
- [x] Remove hardcoded passwords from `docker-compose.yml` (keep for local dev only)
- [x] Enable Redis AUTH and TLS in production config
- [x] Add CORS restrictions to the gateway for production origins
- [x] Enable TLS for Kafka (SASL_SSL) in production client configuration

## Phase 2 — Production readiness 🟠

Get the platform deployable to a real cluster.

- [x] Create Kubernetes manifests for all 6 services (`deploy/k8s/`)
- [x] Add resource requests/limits and HPA scaling rules
- [x] Implement readiness and liveness probes on all services
- [x] Add a `docker-compose.prod.yml` for Docker Swarm as a simpler alternative
- [x] Set up Fluent Bit or similar for log shipping to Elasticsearch/Loki
- [x] Create a Helm chart or Kustomize overlay for environment-specific config
- [x] Document the production deployment steps in `docs/DEPLOYMENT.md`

## Phase 3 — Expanded analytics 🟡

Add more analytical value to the candle data.

- [ ] Technical indicators: SMA, EMA, RSI, MACD, Bollinger Bands (in `query-service/app/domain/indicators.py`)
- [ ] Multi-timeframe candle aggregation (stream-processor already supports configurable intervals)
- [ ] Historical symbol search and discovery API
- [ ] Export candles as CSV/JSON from the query API
- [ ] Real-time WebSocket updates for candle streaming

## Phase 4 — Alerting improvements 🟡

The alert pipeline works but is minimal.

- [ ] Support more than above/below comparators (crossing, percentage change, RSI thresholds)
- [ ] Add notification channels: email (via SendGrid/SES), Slack webhooks, Telegram bot
- [ ] Alert cooldown/throttle to avoid notification storms
- [ ] Alert rule templates for common patterns (e.g., "alert if BTC drops 5% in 1 hour")
- [ ] Dashboard for alert history and acknowledgment

## Phase 5 — Frontend polish 🟢

The frontend is functional but basic.

- [ ] Add authentication flow (login page, JWT storage, session management)
- [ ] Watchlist management UI (create, edit, delete watchlists)
- [ ] Alert rule creation and management UI
- [ ] Trigger history and acknowledgment UI
- [ ] Responsive design improvements for mobile
- [ ] WebSocket integration for real-time price updates

## Phase 6 — Operations & reliability 🟢

Operational maturity for running in production.

- [ ] Chaos engineering tests (kill a Kafka broker, drop a ClickHouse node)
- [ ] Load testing with k6 to establish performance baselines
- [ ] SLO/SLI tracking and error budgets
- [ ] Runbooks for common operational scenarios
- [ ] Automated backup verification
- [ ] On-call alerting for service health

---

## Success criteria

| Metric                    | Target           | Current          |
| ------------------------- | ---------------- | ---------------- |
| Auth in production        | Keycloak JWT     | Keycloak JWT enforced (dev bypass local only) |
| Test coverage             | > 80%            | Partial          |
| API p95 latency           | < 100ms          | Unknown          |
| Uptime                    | 99.9%            | Local dev only   |
| Alert notification channels | ≥ 2 (email + Slack) | Email, Slack, generic webhook |
| Kubernetes deployable     | Yes              | Yes — manifests, overlays, HPAs |
| Documentation             | Complete         | In progress      |
