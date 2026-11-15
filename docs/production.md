# Production deployment notes

This document describes the checked-in deployment options and the external infrastructure they expect. Compose/Kubernetes assets have not been validated against a live production cluster in this documentation review.

## Deployment choices

`docker-compose.prod.yml` is written for Docker Swarm. It deploys application and observability containers, mounts Swarm secrets, and expects Kafka, Redis, PostgreSQL, MongoDB, and ClickHouse endpoints to be supplied externally. Use `make swarm-secrets` after preparing the expected files under `./secrets/`, then `make swarm-deploy`. Swarm ignores Compose `depends_on`; configure restart behavior and operational checks accordingly.

Kubernetes Kustomize manifests are under `deploy/k8s/`. The production overlay includes HPAs for gateway, query-service, and command-service; it requires metrics-server. The data services, ingress/TLS, secret operator, registry, and storage are not provisioned as a complete managed production environment by these manifests. Review the staging overlay carefully: it enables the gateway's development auth bypass.

## External dependencies

Provision supported versions, persistence, TLS, backups, and network policy for:

- Kafka with topic creation/retention and SASL_SSL credentials for production.
- Redis with TLS and AUTH for gateway rate limiting and ingest dedupe.
- PostgreSQL for tenant, watchlist, alert-rule, and trigger records.
- ClickHouse for candle writes and queries.
- MongoDB for raw tick archival.
- Keycloak (or a compatible issuer) with a signing key set and matching issuer/audience claims.
- Prometheus/Grafana/Loki/trace storage or managed equivalents.

No production SLO, capacity target, or restore objective is established in the repository. Set these before launch and exercise recovery procedures.

## Secret settings in service code

Supported file-backed settings include:

| Service | Secret variables |
| --- | --- |
| `api-gateway`, `ingest-service` | `REDIS_PASSWORD_FILE` |
| Kafka clients | `KAFKA_SASL_USERNAME_FILE`, `KAFKA_SASL_PASSWORD_FILE`, optional `KAFKA_TLS_CA_FILE` |
| `command-service`, `alert-service` | `POSTGRES_DSN_FILE` |
| `stream-processor` | `MONGO_URI_FILE`, `CLICKHOUSE_USER_FILE`, `CLICKHOUSE_PASSWORD_FILE` |
| `query-service` | `CLICKHOUSE_USER_FILE`, `CLICKHOUSE_PASSWORD_FILE` |

Exact production validation differs by service. Set `CRYPTOSCOPE_ENV=production` as required, provide mounted files with restrictive permissions, and confirm the corresponding config loader before deploying. The Swarm YAML also references external secret names; create them using the Makefile workflow and its required filenames. Avoid assuming Kubernetes secret manifests automatically make the containers consume file variables.

## Gateway identity and network boundary

Configure `DEV_MODE=false`, `KEYCLOAK_JWKS_URL`, `KEYCLOAK_ISSUER`, `KEYCLOAK_AUDIENCE`, and explicit HTTPS `CORS_ALLOWED_ORIGINS`. Production gateway validation rejects dev bypass and malformed/missing CORS origins. JWT tenant identity is forwarded as headers to internal services. Restrict those services so external callers cannot forge tenant headers by calling them directly.

**Known blockers:** alert-service does not consistently enforce tenant identity on list/detail/ack/delete routes; SSE cannot attach the frontend's Bearer token and currently polls an empty tenant plus a hardcoded symbol; and cross-origin browser writes need `Idempotency-Key` in CORS allow headers. Resolve these before exposing the multi-tenant API. See [roadmap](roadmap.md) and [security](SECURITY.md).

## Scaling and data integrity

Scale Kafka consumers with partition counts and consumer replicas in mind. The repository's production overlay does not autoscale ingest, stream-processor, or alert-service. The gateway and query/command services have CPU-based HPAs. Validate ClickHouse merge behavior and queries at expected volume, Kafka replay and retention, MongoDB retention, Postgres backup/restore, and Redis persistence/failover.

Ingestion dedupe is stored before Kafka publish; a failed publish can suppress a retry for up to 24 hours. Current source logic also maps Coinbase USD quotes into USDT-labeled symbols. Correct these data integrity issues before depending on historical candles or alerts.

## Operations still to define

- SLOs, error budgets, paging thresholds, and ownership.
- Backups and restore tests for every stateful dependency.
- Kafka lag, ingestion freshness, failed source polls, dropped malformed messages, and SSE connection observability.
- Runbooks for key rotation, credential rotation, database recovery, broker outage, replay, and capacity incidents.
- Load and fault-injection baselines.
