# 6. Model multitenancy with row-level tenant_id

Date: 2026-05-24

## Status

Accepted

Implementation note (November 15, 2026): tenant IDs are present in the principal schemas and query paths, but the claim that all access is enforced is not currently true. Alert-service list/detail/acknowledge/delete routes contain cross-tenant gaps. See the P1 finding in [the roadmap](../roadmap.md).

## Context

The platform is multi-tenant. We had to decide between a shared schema with a
tenant column, a schema per tenant, or a database per tenant.

## Decision

Use a shared schema with a row-level `tenant_id` on every tenant-scoped table.
The intended model resolves tenant identity from a verified Keycloak JWT claim
at the gateway and carries it through the call chain. Indexes and ClickHouse
ordering keys lead with `tenant_id` where appropriate.

## Consequences

This keeps operations simple and onboarding a new tenant cheap. It puts the
burden of correctness on always filtering by tenant. The current alert-service
routes demonstrate that this enforcement is incomplete and must be corrected
before multi-tenant production use.
