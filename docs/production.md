# Production deployment — cryptoscope

This guide covers moving cryptoscope from local Docker Compose to a production environment.

## Prerequisites

- Kubernetes cluster (1.26+) or Docker Swarm
- Domain with TLS termination (via Ingress or load balancer)
- External managed services for data stores (recommended) or operator-managed clusters
- Keycloak instance for authentication
- Secrets manager (HashiCorp Vault, AWS Secrets Manager, etc.)

## Environment differences

| Aspect                  | Local dev                      | Production                             |
| ----------------------- | ------------------------------ | -------------------------------------- |
| `DEV_MODE`              | `true` (auth bypass)           | `false` (JWT required)                 |
| Database credentials    | Local development values      | Vault / cloud manager mounted files    |
| Kafka                   | Plaintext, single broker       | SASL_SSL, multi-broker cluster         |
| Redis                   | No auth, no TLS                | AUTH password + TLS                    |
| TLS between services    | None                           | mTLS via service mesh                  |
| ClickHouse              | Single node                    | Replicated cluster                     |
| Observability           | Local Jaeger/Prometheus        | Managed or self-hosted with retention  |
| Log shipping            | stdout JSON                    | Fluent Bit → Elasticsearch / Loki     |

## Required environment variables

Set `CRYPTOSCOPE_ENV=production` on services that use databases. Production
database credentials are read from read-only files rendered by Vault Agent or
an equivalent cloud secrets operator. The application accepts `<NAME>_FILE`
for the credential variables below and fails at startup if a required file is
missing, unreadable, or empty. Plain credential environment variables are
supported only outside production.

| Services | File variable | Contents |
| --- | --- | --- |
| command-service, alert-service | `POSTGRES_DSN_FILE` | PostgreSQL DSN |
| stream-processor | `MONGO_URI_FILE` | MongoDB URI |
| stream-processor, query-service | `CLICKHOUSE_USER_FILE`, `CLICKHOUSE_PASSWORD_FILE` | ClickHouse username and password |

For example, have Vault Agent render each service's secret to `/run/secrets`
and configure the matching `*_FILE` variable to that path (including both
`CLICKHOUSE_USER_FILE` and `CLICKHOUSE_PASSWORD_FILE`). Mount the directory
read-only and restrict file permissions to the service user. For local
development, omit `CRYPTOSCOPE_ENV=production` and use `.env` values.

### api-gateway

```bash
DEV_MODE=false
KEYCLOAK_JWKS_URL=https://auth.example.com/realms/cryptoscope/protocol/openid-connect/certs
KEYCLOAK_ISSUER=https://auth.example.com/realms/cryptoscope
KEYCLOAK_AUDIENCE=cryptoscope-api
API_GATEWAY_HTTP_PORT=8080
QUERY_SERVICE_GRPC_ADDR=query-service:9001
COMMAND_SERVICE_HTTP_ADDR=http://command-service:8002
ALERT_SERVICE_HTTP_ADDR=http://alert-service:8003
REDIS_ADDR=redis-cluster:6379
RATE_LIMIT_REQUESTS_PER_MINUTE=120
RATE_LIMIT_BURST=40
```

### ingest-service

```bash
KAFKA_BROKERS=kafka-0:9093,kafka-1:9093,kafka-2:9093
KAFKA_TOPIC_TICKS=market.ticks.raw
REDIS_ADDR=redis-cluster:6379
BINANCE_BASE_URL=https://api.binance.com
COINBASE_BASE_URL=https://api.exchange.coinbase.com
INGEST_SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT
INGEST_POLL_INTERVAL_SECONDS=15
```

### stream-processor

```bash
KAFKA_BROKERS=kafka-0:9093,kafka-1:9093,kafka-2:9093
KAFKA_TOPIC_TICKS=market.ticks.raw
KAFKA_CONSUMER_GROUP=cryptoscope
MONGO_URI_FILE=/run/secrets/mongo_uri
MONGO_DB=cryptoscope
CLICKHOUSE_ADDR=clickhouse-cluster:9000
CLICKHOUSE_DB=cryptoscope
TENANT_ID=prod-tenant
INTERVALS=1m,5m,1h,1d
```

### query-service

```bash
CLICKHOUSE_HOST=clickhouse-cluster
CLICKHOUSE_HTTP_PORT=8123
CLICKHOUSE_DB=cryptoscope
QUERY_SERVICE_HTTP_PORT=8001
QUERY_SERVICE_GRPC_PORT=9001
```

### command-service

```bash
POSTGRES_DSN_FILE=/run/secrets/postgres_dsn
KAFKA_BROKERS=kafka-0:9093,kafka-1:9093,kafka-2:9093
KAFKA_TOPIC_EVENTS=domain.events
COMMAND_SERVICE_HTTP_PORT=8002
```

### alert-service

```bash
POSTGRES_DSN_FILE=/run/secrets/postgres_dsn
KAFKA_BROKERS=kafka-0:9093,kafka-1:9093,kafka-2:9093
KAFKA_TOPIC_EVENTS=domain.events
KAFKA_TOPIC_ALERTS=alerts.triggers
ALERT_SERVICE_HTTP_PORT=8003
```

## Kubernetes deployment

Kubernetes manifests use Kustomize with overlays for staging and production:

```
deploy/k8s/
├── base/                          # shared manifests (all services, network policies)
├── overlays/
│   ├── staging/                   # staging: DEV_MODE=true, 1 replica per service
│   └── production/                # production: 2-3 replicas, stricter limits
```

### Deploy with Kustomize

```bash
# Staging
make k8s-deploy K8S_OVERLAY=overlays/staging

# Production
make k8s-deploy K8S_OVERLAY=overlays/production

# Or use the staging shortcut
make k8s-deploy-staging
```

### Manual deployment

```bash
# 1. Build images
make k8s-build

# 2. Apply base resources
kubectl apply -k deploy/k8s/base

# 3. Apply environment overlay
kubectl apply -k deploy/k8s/overlays/production

# 4. Verify
make k8s-status
```

## Health checks

Every service exposes health endpoints:

| Endpoint                        | Service        | Checks                    |
| ------------------------------- | -------------- | ------------------------- |
| `GET /healthz`                  | api-gateway    | Upstream services reachable |
| `GET /healthz`                  | command-service| PostgreSQL connectivity   |
| `GET /healthz`                  | query-service  | ClickHouse connectivity   |
| `GET /healthz`                  | alert-service  | PostgreSQL connectivity   |
| `GET /metrics`                  | Go services    | Prometheus metrics        |

## Observability

### Traces

All services export OTLP traces to the OpenTelemetry Collector, which routes them to Jaeger:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_SERVICE_NAMESPACE=cryptoscope
```

### Metrics

Go services expose Prometheus metrics on a configurable port (default `9100`):

```
http://<service>:9100/metrics
```

Grafana dashboards are in `deploy/grafana-dashboards/`. Import them into your Grafana instance.

### Logs

All services emit structured JSON logs. In production, ship them to a log aggregator:

```
service=<name> tenant_id=<id> trace_id=<id> level=info msg="..."
```

Use Fluent Bit or similar to forward to Elasticsearch, Loki, or CloudWatch.

## Scaling considerations

- **ingest-service**: Horizontal scaling via Kafka consumer groups. Each instance polls different symbols or shares the load.
- **stream-processor**: Scales with Kafka partition count. One partition per consumer instance.
- **query-service**: Stateless, scale horizontally behind a load balancer.
- **command-service**: Stateless, scale horizontally. Ensure PostgreSQL can handle the write load.
- **alert-service**: Scales with Kafka consumer groups for event processing.
- **ClickHouse**: Use a replicated cluster for high availability.
- **PostgreSQL**: Use read replicas for query-service reads (future optimization).

## Backup strategy

| Store        | Backup method                          | Frequency    |
| ------------ | -------------------------------------- | ------------ |
| PostgreSQL   | pg_dump / WAL archiving                | Daily + continuous |
| ClickHouse   | ClickHouse backup (clickhouse-backup)  | Daily        |
| MongoDB      | mongodump or oplog                     | Daily        |
| Redis        | RDB snapshots + AOF                    | Continuous   |
| Kafka        | Topic replication factor ≥ 3          | Built-in     |

## CI/CD pipeline

The GitHub Actions workflow `.github/workflows/staging.yaml` automates the full
build → test → push → deploy cycle:

1. **Lint** — Go (`gofmt`, `go vet`) + Python (`ruff`)
2. **Test** — Go tests + Python tests
3. **Build & Push** — All 6 service images + frontend to GHCR (tagged with commit SHA)
4. **Deploy** — Apply kustomize overlay to the staging cluster
5. **Smoke test** — Wait for rollouts, port-forward, health-check the gateway

Triggered on:
- Push to `main` (auto-deploy to staging)
- Manual dispatch with optional image tag override

### Required GitHub secrets

| Secret               | Description                                    |
| -------------------- | ---------------------------------------------- |
| `STAGING_KUBECONFIG` | Base64-encoded kubeconfig for the staging cluster |

### Publishing release images

Tagged releases (`v*`) trigger `.github/workflows/docker-publish.yaml` which
builds and pushes images to GHCR with the version tag.

## Checklist before going live

- [ ] `DEV_MODE=false` in all gateway deployments
- [ ] Keycloak configured and tested with real JWTs
- [ ] All database credentials in secrets manager
- [ ] TLS enabled for all external-facing endpoints
- [ ] Kafka running with SASL_SSL and replication
- [ ] Redis AUTH enabled and TLS configured
- [ ] Grafana dashboards imported and alerting configured
- [ ] Log aggregation pipeline verified
- [ ] Backup and restore tested
- [ ] Rate limiting values tuned for expected traffic
- [ ] Health check endpoints verified from outside the cluster
- [ ] DNS and TLS certificates provisioned
