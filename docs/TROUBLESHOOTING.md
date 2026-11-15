# Troubleshooting

## Compose does not start

- Confirm Docker Engine and Docker Compose v2 are installed and running.
- Run `make ps` and `make logs` to identify the failing container.
- Check host port conflicts for 5173, 8080, 8081, 5432, 8123, 9000, 9090, and 3000.
- Use `make down` to stop the stack. It also removes volumes and deletes local database state.

## UI loads but API requests fail

- Confirm `api-gateway` is healthy with `curl http://localhost:8080/healthz`.
- In local Compose, inspect the frontend nginx proxy and gateway service logs.
- Local Compose enables development authentication behavior. A direct API call can send `X-Tenant-Id`; the frontend demo proxy uses the seeded demo UUID.
- If testing OIDC, check Keycloak at `http://localhost:8081`, configured frontend issuer/client values, and the demo password.
- For a browser client on a separate origin, production CORS currently omits `Idempotency-Key`; write requests will fail preflight.

## No candles appear

- Check ingest logs for Binance/Coinbase polling errors and verify configured symbols are available from both exchanges.
- Confirm Kafka is reachable and the tick topic matches across ingest and processor configuration.
- Check stream-processor logs, ClickHouse connectivity, and configured tenant ID.
- Ingestion currently marks Redis dedupe keys before Kafka publication; after a publish failure, a tick can be skipped for up to 24 hours. See [roadmap](roadmap.md).
- Coinbase USD values are currently emitted under USDT symbol names, so source prices may be combined incorrectly.

## Alert triggers are missing

- Confirm command-service saved the rule with an active status and expected interval/comparator.
- Confirm processor publishes candle events and alert-service consumes the same Kafka topic.
- Percentage-change comparisons depend on process-local rolling price history; a restart causes a warm-up period.
- Inspect PostgreSQL connectivity and alert-service logs. Notifications are disabled until a supported channel is configured.
- Do not use alert tenant filters as an access control boundary; several alert routes currently lack tenant scoping.

## OIDC/JWT failures

- Verify `KEYCLOAK_JWKS_URL`, `KEYCLOAK_ISSUER`, and `KEYCLOAK_AUDIENCE` match the token issuer and client configuration exactly.
- Ensure token has `tenant_id`, is signed with RS256, and has not expired.
- Gateway startup in non-dev mode requires a successful initial JWKS fetch.
- Never enable `DEV_MODE=true` in an externally reachable environment.

## Tests or lint fail to build

- Run a focused target such as `make test-gateway` or `make test-query` to identify the failing module.
- Python test containers may need to build dependencies the first time.
- Run `make help` and inspect `docker-compose.tests.yml` if a documented command is absent.

## Useful commands

```sh
make ps
make logs
make restart svc=api-gateway
make test-gateway
```
