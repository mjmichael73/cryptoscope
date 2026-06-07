# stream-processor

The stream processor consumes raw market ticks from Kafka, archives them for
audit, and folds them into OHLC candles that power the analytics read side.

## What it does

1. Reads ticks from the `market.ticks.raw` topic as part of a consumer group.
2. Archives every raw tick to MongoDB so we can replay or audit later.
3. Aggregates ticks into candles per symbol and interval (1m, 5m, 1h by
   default) using an in-memory rolling window.
4. Persists closed candles to ClickHouse. The target table is a
   `ReplacingMergeTree`, so a redelivered candle converges instead of
   duplicating a row, which keeps the write idempotent.

Offsets are committed only after a message is durably handled, giving
at-least-once processing. On shutdown the processor flushes any open candles so
an in-progress bar is not lost.

## Design notes

- The aggregator and ETL logic depend only on the `RawArchive` and
  `CandleStore` interfaces, so the core is unit tested with fakes and needs no
  running infrastructure.
- Malformed payloads are logged and dropped rather than blocking the partition,
  since a bad message will never succeed on retry.

## Configuration

The service reads its configuration from the environment. See the repository
`.env.example` for the full list. The most relevant variables are:

| Variable                | Purpose                              |
| ----------------------- | ------------------------------------ |
| `KAFKA_BROKERS`         | Comma separated broker list          |
| `KAFKA_TOPIC_TICKS`     | Topic to consume ticks from          |
| `KAFKA_CONSUMER_GROUP`  | Base consumer group name             |
| `MONGO_URI` / `MONGO_DB`| Raw tick archive location            |
| `CLICKHOUSE_*`          | Candle store connection settings     |
| `PROCESSOR_INTERVALS`   | Candle intervals to build            |

## Running the tests

```bash
go test ./...
```
