# 6. Model multitenancy with row-level tenant_id

Date: 2026-05-24

## Status

Accepted

## Context

The platform is multi-tenant. We had to decide between a shared schema with a
tenant column, a schema per tenant, or a database per tenant.

## Decision

Use a shared schema with a row-level `tenant_id` on every tenant-scoped table.
The tenant is resolved from a Keycloak JWT claim at the gateway and carried
through the call chain. Indexes and ClickHouse ordering keys lead with
`tenant_id` so tenant-scoped queries stay fast.

## Consequences

This keeps operations simple and onboarding a new tenant cheap. It puts the
burden of correctness on always filtering by tenant, which we enforce in the
repository layer and cover with tests.
