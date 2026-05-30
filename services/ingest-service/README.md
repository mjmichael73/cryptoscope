# ingest-service

The ingest service is the front door for market data. It polls the public
market data APIs on a schedule, normalizes each response into a common tick,
drops duplicates, and publishes the survivors to Kafka.

## What it does

- Polls Binance and Coinbase public endpoints for the configured symbols.
- Normalizes every response into a `domain.Tick`.
- Deduplicates ticks with a Redis backed key so retries do not create doubles.
- Publishes ticks to the `market.ticks.raw` topic keyed by symbol.

## Configuration

The service reads its configuration from the environment. See the repository
`.env.example` for the full list. The values it cares about are the Kafka
brokers, the Redis address, the source base URLs, the symbol list, and the poll
interval.

## Running the tests

```bash
go test ./...
```

The source tests use `httptest` servers, so they run without touching the real
APIs.
