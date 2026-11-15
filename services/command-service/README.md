# Command service

Python/FastAPI write side for tenant-owned watchlists and alert rules. It persists PostgreSQL records through the repository adapter and publishes domain events to Kafka. Alert-rule deletion is soft deletion; watchlist operations include create/list/read/update/delete.

Routes are proxied by `api-gateway`; request models and validation are in `app/api/schemas.py`. PostgreSQL schema changes use Alembic migrations under `migrations/versions/`. `make migrate` applies migrations and `make migrate-new msg="description"` creates one when the service/database environment is running.

Creates require an `Idempotency-Key`. Run `make test-command` when validation is requested. See the [API reference](../../docs/API.md) and [development guide](../../docs/guides/development.md).
