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
| Log shipping            | stdout JSON                    | Fluent Bit → Loki (Elasticsearch optional) |

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
Redis must be provided by a managed service or operator configured for AUTH and
TLS. Set `REDIS_PASSWORD_FILE` to the mounted Redis password and
`REDIS_TLS_ENABLED=true` for both `api-gateway` and `ingest-service`; both
services reject production startup without a password and TLS. The Redis TLS
client verifies the server certificate using the container's system trust
store, so install the issuing CA in the image when using a private CA.

Kafka brokers must enable SASL over TLS for production listeners. Set
`KAFKA_SECURITY_PROTOCOL=SASL_SSL`, `KAFKA_SASL_MECHANISM=SCRAM-SHA-512`, and
mount the broker-issued username and password as
`KAFKA_SASL_USERNAME_FILE` and `KAFKA_SASL_PASSWORD_FILE` for every service
that produces or consumes Kafka messages. The clients verify broker
certificates using the system trust store; set `KAFKA_TLS_CA_FILE` to an
additional CA bundle when a private CA is used. The service startup config
rejects plaintext production settings or missing credential files. Do not
place Kafka credentials directly in environment variables in production.

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
REDIS_PASSWORD_FILE=/run/secrets/redis_password
REDIS_TLS_ENABLED=true
CORS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
RATE_LIMIT_REQUESTS_PER_MINUTE=120
RATE_LIMIT_BURST=40
```

Set `CORS_ALLOWED_ORIGINS` on the gateway to the exact HTTPS origins of the
browser clients. Separate origins with commas and omit URL paths (for example,
`https://app.example.com,https://admin.example.com`). The gateway rejects
missing, wildcard, HTTP, or malformed origins during production startup.

### ingest-service

```bash
KAFKA_BROKERS=kafka-0:9093,kafka-1:9093,kafka-2:9093
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=SCRAM-SHA-512
KAFKA_SASL_USERNAME_FILE=/run/secrets/kafka_sasl_username
KAFKA_SASL_PASSWORD_FILE=/run/secrets/kafka_sasl_password
KAFKA_TLS_CA_FILE=/run/secrets/kafka_ca.pem
KAFKA_TOPIC_TICKS=market.ticks.raw
REDIS_ADDR=redis-cluster:6379
REDIS_PASSWORD_FILE=/run/secrets/redis_password
REDIS_TLS_ENABLED=true
BINANCE_BASE_URL=https://api.binance.com
COINBASE_BASE_URL=https://api.exchange.coinbase.com
INGEST_SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT
INGEST_POLL_INTERVAL_SECONDS=15
```

### stream-processor

```bash
KAFKA_BROKERS=kafka-0:9093,kafka-1:9093,kafka-2:9093
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=SCRAM-SHA-512
KAFKA_SASL_USERNAME_FILE=/run/secrets/kafka_sasl_username
KAFKA_SASL_PASSWORD_FILE=/run/secrets/kafka_sasl_password
KAFKA_TLS_CA_FILE=/run/secrets/kafka_ca.pem
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
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=SCRAM-SHA-512
KAFKA_SASL_USERNAME_FILE=/run/secrets/kafka_sasl_username
KAFKA_SASL_PASSWORD_FILE=/run/secrets/kafka_sasl_password
KAFKA_TLS_CA_FILE=/run/secrets/kafka_ca.pem
KAFKA_TOPIC_EVENTS=domain.events
COMMAND_SERVICE_HTTP_PORT=8002
```

### alert-service

```bash
POSTGRES_DSN_FILE=/run/secrets/postgres_dsn
KAFKA_BROKERS=kafka-0:9093,kafka-1:9093,kafka-2:9093
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=SCRAM-SHA-512
KAFKA_SASL_USERNAME_FILE=/run/secrets/kafka_sasl_username
KAFKA_SASL_PASSWORD_FILE=/run/secrets/kafka_sasl_password
KAFKA_TLS_CA_FILE=/run/secrets/kafka_ca.pem
KAFKA_TOPIC_EVENTS=domain.events
KAFKA_TOPIC_ALERTS=alerts.triggers
ALERT_SERVICE_HTTP_PORT=8003
```

## Kubernetes deployment

Kubernetes manifests use Kustomize with overlays for staging and production:

```
deploy/k8s/
├── base/                          # shared manifests (all services, frontend, Loki, Fluent Bit, network policies)
├── overlays/
│   ├── staging/                   # staging: DEV_MODE=true, fixed 1 replica per service
│   └── production/                # production: HPAs, stricter limits
```

### Autoscaling

The production overlay ships HorizontalPodAutoscalers for the stateless HTTP
tier — `api-gateway` (3–8 replicas, CPU 70%), `query-service` (3–8, CPU 75%)
and `command-service` (2–6, CPU 75%) — each with a memory ceiling and a
5-minute scale-down stabilization window. The HPAs own the replica counts of
these Deployments: the overlay deliberately sets no static `replicas` for
them, so re-applying the overlay never fights the autoscaler. Prerequisite:
metrics-server must be installed in the cluster.

`ingest-service`, `stream-processor` and `alert-service` have no CPU-based
HPA on purpose: they are Kafka consumers whose parallelism is bounded by the
topic partition count. Scale them by adding partitions and replicas together;
if partitions themselves should drive scaling, KEDA is the intended path.

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

All services emit structured JSON logs:

```
service=<name> tenant_id=<id> trace_id=<id> level=info msg="..."
```

Fluent Bit ships container logs to Loki, which is provisioned as a Grafana
datasource:

- **Kubernetes**: the `fluent-bit` DaemonSet (`deploy/k8s/base/fluent-bit.yaml`)
  tails `/var/log/containers` on every node and the single-node `loki`
  Deployment (`deploy/k8s/base/loki.yaml`) stores them. Point the DaemonSet's
  `LOKI_HOST`/`LOKI_PORT` env at a managed Loki to ship elsewhere.
- **Docker Swarm**: `loki` and `fluent-bit` run from `docker-compose.prod.yml`
  using `deploy/loki/loki-config.yaml` and `deploy/fluent-bit/fluent-bit.conf`.
- **Local development**: opt-in with
  `docker compose --profile logs up -d loki fluent-bit`.

Labels stay low-cardinality (`app`, `service`, `level`, `tenant_id`);
`trace_id` remains in the log body, so Jaeger's "logs for this trace" link in
Grafana works without exploding label cardinality. Retention is 7 days. To
switch to Elasticsearch, enable the commented `es` output in the Fluent Bit
configs — the JSON field shape is designed to index cleanly either way.

## Docker Swarm deployment

`docker-compose.prod.yml` is the simpler alternative for clusters without
Kubernetes. It deploys the six services, the frontend and observability
(otel-collector, Jaeger, Prometheus, Grafana, Loki, Fluent Bit) while Kafka,
PostgreSQL, ClickHouse, MongoDB and Redis stay externally managed.

```bash
# 1. Environment: copy .env.example and set the production values listed in
#    its Docker Swarm section (Kafka SASL_SSL endpoints, Redis AUTH+TLS,
#    Keycloak, CORS origins, CRYPTOSCOPE_IMAGE_TAG).

# 2. Secrets: write each credential to secrets/<name>.txt (git-ignored),
#    then create the Swarm secrets (idempotent):
make swarm-secrets

# 3. Images: push cryptoscope/* images to a registry reachable by every node
#    (CI publishes them), or build on the manager with make k8s-build.

# 4. Deploy:
make swarm-deploy
docker stack services cryptoscope
```

Notes:

- Swarm ignores `depends_on`; tasks restart with `restart_policy` until
  dependencies accept connections — watch `docker service ps` during rollout.
- No autoscaling in Swarm: replicas are static. Scale with
  `docker service scale cryptoscope_api-gateway=5` as load grows.
- Port bindings use Swarm ingress mode: 80 (frontend), 8080 (api-gateway),
  plus Grafana/Prometheus/Jaeger for operators. Terminate TLS on the edge
  load balancer.
- Redeploy by building new images and running `make swarm-deploy` again.

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
- [ ] metrics-server installed and HPAs behaving on the production overlay
- [ ] Backup and restore tested
- [ ] Rate limiting values tuned for expected traffic
- [ ] Health check endpoints verified from outside the cluster
- [ ] DNS and TLS certificates provisioned
