# API gateway

Go HTTP edge for client REST and SSE. It validates Keycloak JWTs outside dev mode, resolves/forwards tenant identity, rate-limits `/v1/*`, translates query requests to gRPC, and proxies command/alert HTTP routes.

Local HTTP defaults to port 8080. Configuration is in `internal/config/config.go`; route wiring is in `internal/gateway/gateway.go`. The gateway's `/healthz` is a process check, not a full dependency readiness check.

Known issues affecting browser writes, candle export, and SSE are documented in [the API reference](../../docs/API.md) and [roadmap](../../docs/roadmap.md). Run `make test-gateway` when validation is requested.
