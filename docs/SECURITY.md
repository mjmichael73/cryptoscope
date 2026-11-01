# Security — cryptoscope

## Reporting a vulnerability

If you discover a security vulnerability, please report it privately. **Do not open a public GitHub issue.** Contact the maintainer directly at `mojimich2015@gmail.com`.

## Known issues (dev mode)

The local development stack runs with several security features disabled:

| Issue                      | Dev mode               | Production target    |
| -------------------------- | ---------------------- | -------------------- |
| `DEV_MODE=true`            | Bypasses JWT auth      | Disabled             |
| Development DB passwords  | Sample values in ignored `.env` | Vault / cloud manager mounted files |
| No mTLS between services   | Plaintext internal comms | mTLS via service mesh |
| Kafka plaintext            | No TLS or SASL         | SASL_SSL             |
| Grafana development password | Sample value in ignored `.env` | Set a secret on deploy |
| Redis no auth              | No password            | Require auth + TLS   |

These are tracked in the roadmap under "Security Hardening."

## Authentication

- **Gateway JWT auth**: Outside dev mode, the `api-gateway` validates Keycloak JWT signatures using RS256 and checks the configured issuer, audience, and token time claims. Startup fails if auth configuration is incomplete or the initial JWKS fetch fails. Set `APP_ENV=production` (or `ENVIRONMENT=production`) to reject `DEV_MODE=true`.
- **Keycloak config** (production):
  - `KEYCLOAK_JWKS_URL` — JWKS endpoint for token verification
  - `KEYCLOAK_ISSUER` — Expected issuer claim
  - `KEYCLOAK_AUDIENCE` — Expected audience claim
- Every authenticated access token must contain a non-empty `tenant_id` claim. The gateway ignores client-supplied tenant identity on protected routes and propagates the verified claim; a user `sub` is not treated as a tenant ID.

## Multi-tenant isolation

Every query is scoped by `tenant_id`. The gateway resolves the tenant from the JWT and propagates it via gRPC metadata. All data stores filter on `tenant_id` at the row level.

**Enforcement points:**
- `api-gateway`: extracts `tenant_id` from JWT, passes in gRPC metadata and HTTP headers
- `command-service`: validates tenant ownership before writes
- `query-service`: filters all reads by `tenant_id`
- `stream-processor`: tags candles with `TENANT_ID` from env

## Rate limiting

The gateway applies Redis-backed token-bucket rate limiting per tenant:

```yaml
RATE_LIMIT_REQUESTS_PER_MINUTE: "120"
RATE_LIMIT_BURST: "40"
```

These values are configurable via environment variables.

## Secrets management

- **Never commit secrets.** The `.env` file is gitignored; `.env.example` shows required variables.
- **Production database credentials**: set `CRYPTOSCOPE_ENV=production` and provide credentials through read-only files rendered by Vault Agent or a cloud secrets operator. The services support `POSTGRES_DSN_FILE`, `MONGO_URI_FILE`, `CLICKHOUSE_USER_FILE`, and `CLICKHOUSE_PASSWORD_FILE`; missing, unreadable, or empty required files fail service startup. Plain credential environment values remain for local development.
- **Local development**: copy `.env.example` to ignored `.env` and keep credentials there. Compose requires these variables and contains no embedded password values. Never commit the values.
- Rotate credentials in the secret manager and restart services after rotation; the current integration reads files at startup.

## Dependency security

```bash
# Go — check for vulnerable dependencies
go list -m all | nancy sleuth

# Python — audit installed packages
pip audit

# Frontend — audit npm packages
npm audit

# Go vet (catches common issues)
make lint-go
```

Keep dependencies updated regularly. The `Makefile` lint targets catch many issues at development time.

## Network security

- **Local dev**: All services communicate over Docker's internal network (no TLS).
- **Production**: Add a service mesh (e.g., Istio, Linkerd) for mTLS between services, or configure TLS at each hop.
- **CORS**: In production, `api-gateway` requires `CORS_ALLOWED_ORIGINS` to list one or more explicit HTTPS origins (comma-separated, such as `https://app.example.com`). Wildcards, HTTP origins, credentials, paths, queries, and fragments are rejected at startup. The gateway returns CORS headers only for listed origins; local development may leave the list empty.

## Logging and audit

- All services emit structured JSON logs with `service`, `tenant_id`, and `trace_id`.
- OpenTelemetry traces are exported to Jaeger for distributed tracing.
- Sensitive fields (passwords, tokens) must never appear in logs.

## Recommendations for production

1. Replace all hardcoded credentials with a secrets manager
2. Disable `DEV_MODE` and configure Keycloak properly
3. Enable TLS for Kafka, Redis, PostgreSQL, and ClickHouse
4. Add mTLS between internal services
5. Set up alerting on auth failures and rate-limit hits
6. Rotate Grafana admin password before deploying
7. Restrict CORS to known frontend origins
8. Enable Redis AUTH and TLS
