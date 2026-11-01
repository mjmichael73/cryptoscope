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
| `docker-compose.tests.yml`    | Test and lint runner containers      |

## Building images

```bash
make build       # build all Docker images without starting
```

Production images are built from service-specific `Dockerfile`s. Python services use multi-stage builds. The frontend uses nginx for production serving.

## Production deployment

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
| `KAFKA_BROKERS`             | all Go services  | Comma-separated Kafka broker addresses   |
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
| `LOG_LEVEL`                 | all              | `debug`, `info`, `warn`, `error`        |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | gateway    | Rate limit per tenant per minute         |
| `SMTP_HOST`                | alert-service  | SMTP server for email notifications      |
| `SMTP_FROM` / `SMTP_TO`   | alert-service  | Sender and recipient addresses            |
| `SLACK_WEBHOOK_URL`        | alert-service  | Slack incoming webhook URL               |
| `ALERT_WEBHOOK_URL`        | alert-service  | Generic webhook POST URL                 |

## Troubleshooting

See [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.
