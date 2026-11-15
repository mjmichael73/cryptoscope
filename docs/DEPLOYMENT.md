# Deployment and local setup

## Local Docker Compose

Docker Compose v2 is required. This checkout has no `.env.example`. Before `make up`, set `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`, `MONGO_ROOT_USERNAME`, `MONGO_ROOT_PASSWORD`, and `POSTGRES_DSN` in `.env`. The Compose file also expects the external Docker network `shared-services-network` and a PostgreSQL instance reachable on that network; PostgreSQL is not a service in this Compose file. Inspect `docker-compose.yml` before exposing ports or sharing the environment.

```sh
make up       # build and start the complete local stack, including Keycloak
make ps
make logs
make seed     # create the demo watchlist and alert rule
make down     # stop services and remove Compose-managed volumes
```

`make up-all` starts backend and observability containers, then runs the Vite frontend on the host at port 5173. That command requires Node/npm. The frontend container serves the UI on host port 5173; the gateway is on 8080 and local Keycloak on 8081.

`make up` enables the `dev` Compose profile, which starts Keycloak alongside the frontend. It uses realm `cryptoscope`, client `cryptoscope-frontend`, user `demo@cryptoscope.local`, and `KEYCLOAK_DEMO_PASSWORD` (default `demo-password`). Keycloak and gateway dev defaults are for local use only. `make seed` calls the gateway and assumes the stack is running in its local dev configuration.

## Local service endpoints

| Component | Port | Notes |
| --- | ---: | --- |
| Frontend | 5173 | Vite or frontend container |
| API gateway | 8080 | Public local HTTP/SSE edge |
| Keycloak | 8081 | Started by `make up` via the `dev` profile |
| Query-service | 8001 / 9001 | HTTP / gRPC; internal use |
| Command-service | 8002 | Internal HTTP |
| Alert-service | 8003 | Internal HTTP |
| PostgreSQL | external | Shared service on `shared-services-network`; not defined in this Compose file |
| ClickHouse | 8123 / 9000 | HTTP / native protocol |
| MongoDB | 27017 | Raw tick archive |
| Redis | 6380 | Host port mapped to container port 6379 |
| Kafka | 9092 | Local broker |
| Prometheus / Grafana | 9090 / 3000 | Metrics and dashboards |

Check the Compose file for exact published ports and credentials before relying on this table in a modified environment.

## Compose files

- `docker-compose.yml`: local application stack, data stores, Keycloak, and local observability services.
- `docker-compose.tests.yml`: isolated test and lint runners using source bind mounts.
- `docker-compose.prod.yml`: Docker Swarm application/observability stack using external data services and Swarm secrets. It does not provision the external Postgres, Kafka, Redis, ClickHouse, or MongoDB clusters.

## Kubernetes

Kustomize assets are under `deploy/k8s/base` with `staging` and `production` overlays. Build/apply through `make k8s-build`, `make k8s-deploy K8S_OVERLAY=overlays/staging`, or `make k8s-deploy K8S_OVERLAY=overlays/production`. These manifests are deployment templates, not a turnkey cluster: supply the required secrets, data stores, ingress/TLS, image registry, DNS, and metrics-server for HPAs. The staging overlay explicitly sets `DEV_MODE=true` and must remain isolated.

## Production configuration checklist

- Set `CRYPTOSCOPE_ENV=production` and `DEV_MODE=false` where supported.
- Configure Keycloak JWKS URL, issuer, and audience on the gateway.
- Set explicit HTTPS `CORS_ALLOWED_ORIGINS` on the gateway. Current CORS code omits the frontend's `Idempotency-Key` request header; see the roadmap before using a separate browser origin.
- Provide Kafka SASL_SSL credentials and CA trust as mounted files for Kafka clients.
- Provide PostgreSQL, MongoDB, ClickHouse, and Redis endpoints and credentials. Components use `_FILE` settings selectively; inspect `docs/production.md` and each service config because not every secret is uniformly file-backed.
- Configure durable storage, retention, backups, restore procedures, alerting, and restricted network access for internal service ports.
- Resolve the security and reliability issues in [the roadmap](roadmap.md), especially alert tenant isolation and SSE authorization/scoping, before multi-tenant exposure.

Full environment variables and limitations are listed in [production deployment](production.md). Authentication and known gaps are covered in [security](SECURITY.md).
