# api-gateway

Edge REST API for cryptoscope. Authenticates requests, enforces rate limits,
resolves tenant context, and routes to the appropriate backend service:

- **GET /v1/candles**, **GET /v1/indicators**, **GET /v1/symbols** → query-service (gRPC)
- **POST /v1/watchlists**, **POST /v1/alert-rules** → command-service (HTTP)
- **GET /healthz** → returns service health
