# Ingest service

Go polling service that fetches current prices from Binance and Coinbase public REST endpoints, validates and deduplicates ticks through Redis, and publishes normalized records to Kafka (`market.ticks.raw` by default).

Symbols and poll interval are configured with `INGEST_SYMBOLS` and `INGEST_POLL_INTERVAL_SECONDS`; endpoints are configured with `BINANCE_BASE_URL` and `COINBASE_BASE_URL`. The current Coinbase adapter maps `BTCUSDT` to `BTC-USD` but retains the `BTCUSDT` label, mixing quote currencies in downstream aggregation; see the [roadmap](../../docs/roadmap.md).

The dedupe key is stored before Kafka publication. A failed publish can suppress retry for the key TTL (24 hours in the current main configuration). This integrity issue is also tracked in the roadmap. Run `make test-ingest` when validation is requested.
