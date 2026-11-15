# Development guide

## Prerequisites

Docker Engine and Docker Compose v2. `make up-all` and the host frontend targets also require Node.js and npm. The repository does not include `.env.example`; Compose requires five environment values plus an external Docker network and PostgreSQL service. See [deployment](../DEPLOYMENT.md) before the first run.

## Start the application

```sh
make up       # apply PostgreSQL migrations, then start frontend, services, and Keycloak
make ps
make logs
make seed     # after services are ready
```

Open `http://localhost:5173`; the gateway is at `http://localhost:8080`. Keycloak is at `http://localhost:8081` for local sign-in. Use `make down` with care: it deletes Compose volumes and local data.

`make up` applies command-service Alembic migrations before bringing up application services. When starting services directly with Docker Compose, command-service applies migrations as part of its own startup.

For Vite hot reload, run `make up-all`; it starts the backend and then runs `npm run dev` from `frontend/`. Alternatively, `make frontend-dev` starts Vite when the backend is already running.

## Repository map

- `proto/cryptoscope/v1/`: protobuf source contracts.
- `services/`: three Go and three Python services.
- `libs/go/`, `libs/python/`: shared modules.
- `frontend/`: React/TypeScript application and Vite config.
- `services/command-service/migrations/`: command-service Alembic migrations.
- `deploy/`: Kubernetes, Keycloak, and observability configuration.
- `docs/`: API, architecture, deployment, testing, security, ADR, and operations docs.

## Common changes

For gRPC contract edits, update `.proto` files and run `make proto`. For command database schema changes, add an Alembic migration with `make migrate-new msg="description"`, review it, then apply with `make migrate`. Use service-specific Make targets for tests and lint; see [testing](../testing.md).

## Local API identity

The gateway's local `DEV_MODE=true` bypasses JWT checks. Direct calls can supply `X-Tenant-Id`; the frontend development proxy supplies the fixed seeded demo UUID. The gateway's own fallback string (`demo-tenant`) differs from that UUID, so use the seeded proxy/header value for command-service writes backed by PostgreSQL.

Never copy development credentials or auth bypass settings into an externally reachable environment. Review [security](../SECURITY.md) and [roadmap](../roadmap.md) before changing tenant-sensitive code.

## Stack and workflows

The Makefile is the source of truth for available commands. `make help` lists targets. The demo seed command is `make seed` (there is no `make bootstrap` target).
