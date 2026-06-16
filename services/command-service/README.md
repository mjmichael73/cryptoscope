# command-service

The command service is the write side of the CQRS split. It owns tenant
configuration (watchlists and alert rules), enforces the invariants around
them, and emits domain events that the read side and the alert service consume.

## Responsibilities

- Accept write commands over REST (and, in production, gRPC through the
  gateway).
- Validate input and persist it to PostgreSQL.
- Emit a domain event to the `domain.events` topic after the write commits.

## Idempotency

Every command carries a client supplied `Idempotency-Key`. The service records
the key together with the id of the resource it produced in a
`processed_commands` ledger. A retry with the same key returns the original id
instead of creating a duplicate, which makes the create endpoints safe to call
again after a timeout.

The event is published only after the database transaction commits, so a
consumer never observes an event for a change that did not persist.

## Multitenancy

Tenant identity arrives as trusted headers (`X-Tenant-Id`, `X-Tenant-Slug`)
that the gateway sets after validating the Keycloak token. Every row carries a
`tenant_id`, and indexes lead with it so a tenant's data stays cheap to reach.

## Layout

- `app/domain` holds the use cases, commands, events, and the repository port.
- `app/infra` holds the SQLAlchemy repository and the Kafka publisher.
- `app/api` holds the FastAPI routes and request models.
- `migrations` holds the Alembic schema history.

## Running the tests

```bash
pip install -e ../../libs/python -e ".[dev]"
pytest
```

The unit tests exercise the use cases against an in-memory repository, so they
need no database. Schema migrations and the SQLAlchemy adapter are covered by
the integration suite that runs against a real Postgres.

## Migrations

```bash
alembic upgrade head
```
