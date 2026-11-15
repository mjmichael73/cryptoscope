# Stream processor

Go Kafka consumer that archives raw ticks in MongoDB, aggregates configured intervals, persists candles to ClickHouse, and publishes `candle_updated` events for alert evaluation. Its offset handling aims for at-least-once processing after durable work.

Configuration includes `KAFKA_TOPIC_TICKS`, `KAFKA_CONSUMER_GROUP`, `TENANT_ID`, `INTERVALS`, ClickHouse settings, and MongoDB settings. ClickHouse creates a `ReplacingMergeTree` candle table on startup.

Malformed JSON currently logs and returns success, so the message can be committed without a dead-letter copy. See the [roadmap](../../docs/roadmap.md). Run `make test-processor` when validation is requested.
