# Security posture and known gaps

This is a code-informed inventory, not a certification or complete security audit. The gateway is designed as the client edge, but service-level authorization and network boundaries still matter.

## Implemented controls

- Outside development mode, the gateway validates RS256 JWT signatures using Keycloak JWKS and checks issuer, audience, expiry, and a required `tenant_id` claim.
- The gateway derives tenant identity from verified JWT claims and forwards tenant headers to downstream services.
- The gateway has Redis-backed rate limiting, configured security headers, and explicit origin matching when CORS origins are configured.
- Production configuration has validation for gateway dev bypass, Redis password/TLS, HTTPS CORS origins, and Kafka transport settings in relevant services.
- Compose and Swarm configuration supports secret files/Swarm secrets for selected credentials.

## High-priority gaps

1. **Alert tenant isolation is incomplete.** Alert-service list filters accept a caller-provided tenant ID; rule detail, trigger acknowledgment, and trigger deletion omit tenant predicates. A valid gateway token does not correct these route-level gaps. Do not expose these endpoints as a multi-tenant production API until fixed.
2. **SSE is not usable with the frontend's production auth flow.** Browser `EventSource` does not send the stored Bearer token. The handler also queries an empty tenant and a hardcoded symbol, rather than the authenticated tenant and selected series.
3. **Cross-origin write preflight omits `Idempotency-Key`.** This is the header sent by the frontend for writes, but it is absent from gateway's CORS allow-header list.
4. **Internal services must not be publicly reachable.** Tenant headers are trusted by downstream APIs. Network policy and authentication should prevent untrusted direct access.

See [roadmap](roadmap.md) for issue details and fixes to track.

## Development-only behavior

`DEV_MODE=true` disables gateway JWT validation. The gateway accepts `X-Tenant-Id` or supplies `demo-tenant`. The frontend's local nginx proxy injects a fixed demo tenant UUID. These values are for the local Compose setup only. The Kubernetes staging overlay enables `DEV_MODE=true`; keep it private and change it before sharing or exposing the environment.

The repository contains demo credentials and Compose fallback credentials. Replace them for any shared deployment. The current checkout has no `.env.example`; do not assume one exists.

## Other security considerations

- Ensure all client traffic uses TLS at the edge; gateway HSTS alone does not terminate TLS.
- Scope Redis, Kafka, ClickHouse, MongoDB, and PostgreSQL credentials to the minimum required privileges.
- Keep service ports internal and apply network policies.
- Review data retention, user data deletion, and backups for market ticks and alert history.
- Avoid high-cardinality or sensitive identifiers in metric labels and logs.
- Rotate Keycloak signing keys and service credentials; verify JWKS refresh and outage behavior operationally.

Report security issues privately to the repository owner rather than opening a public issue with exploit details.
