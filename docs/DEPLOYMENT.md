# Deployment — cryptoscope

## Local development

The full stack runs with Docker Compose. The only host dependency is Docker.
Compose reads database and Grafana credentials from `.env`; the checked-in
`.env.example` contains sample values for local development only. Copy it
before starting the stack, and replace those values in any shared environment.
Compose intentionally rejects missing credentials instead of embedding
passwords in `docker-compose.yml`.

```bash
cp .env.example .env

# Start everything (backend + frontend via Docker)
make up

# Start backend + frontend dev server with hot-reload
make up-all

# Tail logs from all services
make logs

# Stop and clean up
make down
```

The frontend is served at `http://localhost:5173`. The API gateway is at `http://localhost:8080`.

### Seeding demo data

```bash
make seed    # creates a demo tenant and tracked symbols
```

### Running database migrations

```bash
make migrate         # apply pending Alembic migrations
make migrate-new msg="description"  # create a new migration
```

## Service ports (local dev)

| Service            | Port  | URL                                  |
| ------------------ | ----- | ------------------------------------ |
| api-gateway        | 8080  | http://localhost:8080                |
| query-service      | 8001  | http://localhost:8001                |
| command-service    | 8002  | http://localhost:8002                |
| alert-service      | 8003  | http://localhost:8003                |
| frontend           | 5173  | http://localhost:5173                |
| PostgreSQL         | 5432  | postgres://localhost:5432            |
| ClickHouse         | 8123  | http://localhost:8123 (HTTP)         |
| ClickHouse         | 9000  | Native protocol                      |
| MongoDB            | 27017 | mongodb://localhost:27017            |
| Redis              | 6379  | redis://localhost:6379               |
| Kafka              | 9092  | localhost:9092                       |
| Prometheus         | 9090  | http://localhost:9090                |
| Grafana            | 3000  | http://localhost:3000                |

## Docker Compose files

| File                           | Purpose                              |
| ------------------------------ | ------------------------------------ |
| `docker-compose.yml`          | Full local development stack         |
| `docker-compose.prod.yml`     | Production stack for Docker Swarm    |
| `docker-compose.tests.yml`    | Test and lint runner containers      |

## Building images

```bash
make build       # build all Docker images without starting
```

Production images are built from service-specific `Dockerfile`s. Python services use multi-stage builds. The frontend uses nginx for production serving.

## Log shipping (Fluent Bit → Loki)

All services emit structured JSON logs (`service`, `tenant_id`, `trace_id`).
Fluent Bit ships container logs to Loki, and a Loki datasource is
auto-provisioned in Grafana.

- Local development is opt-in: `docker compose --profile logs up -d loki fluent-bit`
- The Swarm stack (`docker-compose.prod.yml`) runs `loki` and `fluent-bit` always
- Kubernetes runs a Fluent Bit DaemonSet and single-node Loki
  (`deploy/k8s/base/fluent-bit.yaml`, `deploy/k8s/base/loki.yaml`)

Labels stay low-cardinality: `app`, `service`, `level`, `tenant_id`.
`trace_id` deliberately stays in the log body — correlate traces to logs via
the Jaeger datasource in Grafana. To ship to Elasticsearch instead, enable
the commented `es` output in `deploy/fluent-bit/fluent-bit.conf`.

## Production deployment

### Docker Swarm (`docker-compose.prod.yml`)

Deploys the application tier plus observability to a Swarm cluster as a
simpler alternative to the Kubernetes manifests. Data stores stay externally
managed, credentials are mounted as Docker secrets, and Kafka uses SASL_SSL.

```bash
# 1. Set production values in .env (see the Docker Swarm section at the end
#    of .env.example): KAFKA_BROKERS, REDIS_ADDR, CLICKHOUSE_HOST,
#    CLICKHOUSE_ADDR, TENANT_ID, KEYCLOAK_*, CORS_ALLOWED_ORIGINS,
#    CRYPTOSCOPE_IMAGE_TAG.

# 2. Write each credential to secrets/<name>.txt (git-ignored) and create the
#    Swarm secrets. Idempotent: existing secrets are skipped.
make swarm-secrets

# 3. Push cryptoscope/* images to a registry reachable by every node and set
#    CRYPTOSCOPE_IMAGE_TAG (CI publishes them), or build on the manager:
#    make k8s-build

# 4. Deploy
make swarm-deploy       # docker stack deploy -c docker-compose.prod.yml cryptoscope
docker stack services cryptoscope

# Tear down
make swarm-remove
```

Swarm ignores `depends_on`, so services restart with `restart_policy` until
their dependencies accept connections — expected cold-start behaviour. There
is no HPA in Swarm; replica counts are static and scaled manually with
`docker service scale`.

### Kubernetes

See [docs/production.md](production.md) for the full production deployment guide, including:

- Required environment variables per service
- Kubernetes deployment steps
- Health check endpoints
- Observability setup
- Scaling considerations
- Backup strategy

## Environment variables

All configuration is done via environment variables. See `.env.example` for the full list. Key variables:

| Variable                    | Service          | Description                              |
| --------------------------- | ---------------- | ---------------------------------------- |
| `DEV_MODE`                  | api-gateway      | `true` to bypass JWT auth (dev only)     |
| `APP_ENV`                   | api-gateway      | Set to `production` to forbid dev auth bypass; `ENVIRONMENT` is also accepted |
| `KEYCLOAK_JWKS_URL`         | api-gateway      | Required outside dev mode; signing key endpoint |
| `KEYCLOAK_ISSUER`           | api-gateway      | Required expected JWT issuer |
| `KEYCLOAK_AUDIENCE`         | api-gateway      | Required expected JWT audience |
| `CORS_ALLOWED_ORIGINS`      | api-gateway      | Comma-separated explicit HTTPS origins; required in production |
| `KAFKA_BROKERS`             | all Go services  | Comma-separated Kafka broker addresses   |
| `KAFKA_SECURITY_PROTOCOL`   | all Kafka clients | `PLAINTEXT` locally; `SASL_SSL` in production |
| `KAFKA_SASL_USERNAME_FILE` / `KAFKA_SASL_PASSWORD_FILE` | all Kafka clients | Mounted Kafka SASL credentials in production |
| `KAFKA_TLS_CA_FILE`         | all Kafka clients | Optional additional CA bundle for private broker certificates |
| `POSTGRES_DSN`              | command, alert   | PostgreSQL connection string             |
| `POSTGRES_DSN_FILE`         | command, alert   | Production PostgreSQL DSN secret file     |
| `MONGO_URI_FILE`            | stream-processor | Production MongoDB URI secret file        |
| `CLICKHOUSE_USER_FILE`      | processor, query | Production ClickHouse username file        |
| `CLICKHOUSE_PASSWORD_FILE`  | processor, query | Production ClickHouse password file       |
| `CRYPTOSCOPE_ENV`           | DB services      | Set to `production` to require secret files |
| `MONGO_ROOT_USERNAME`       | local Compose    | Local MongoDB root username                |
| `MONGO_ROOT_PASSWORD`       | local Compose    | Local MongoDB root password                |
| `GRAFANA_ADMIN_USER`        | local Compose    | Local Grafana admin username               |
| `GRAFANA_ADMIN_PASSWORD`    | local Compose    | Local Grafana admin password               |
| `CLICKHOUSE_HOST`           | query-service    | ClickHouse host                          |
| `REDIS_ADDR`                | gateway, ingest  | Redis address                            |
| `REDIS_PASSWORD`            | gateway, ingest  | Local Redis AUTH password                 |
| `REDIS_PASSWORD_FILE`       | gateway, ingest  | Redis AUTH secret file; required in production |
| `REDIS_TLS_ENABLED`         | gateway, ingest  | Enable verified TLS; required in production   |
| `CRYPTOSCOPE_ENV`           | gateway, ingest  | Set to `production` to require Redis AUTH/TLS |
| `CRYPTOSCOPE_IMAGE_TAG`     | prod compose     | Image tag for all `cryptoscope/*` images in `docker-compose.prod.yml` |
| `LOG_LEVEL`                 | all              | `debug`, `info`, `warn`, `error`        |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | gateway    | Rate limit per tenant per minute         |
| `SMTP_HOST`                | alert-service  | SMTP server for email notifications      |
| `SMTP_FROM` / `SMTP_TO`   | alert-service  | Sender and recipient addresses            |
| `SLACK_WEBHOOK_URL`        | alert-service  | Slack incoming webhook URL               |
| `ALERT_WEBHOOK_URL`        | alert-service  | Generic webhook POST URL                 |

## Troubleshooting

See [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.
