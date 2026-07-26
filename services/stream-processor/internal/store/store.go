// Package store defines the persistence ports for the stream processor and the
// concrete adapters that implement them.
//
// The ETL logic depends only on the interfaces here, which keeps it decoupled
// from ClickHouse and MongoDB and lets us test it with fakes.
package store

import (
	"context"

	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/domain"
)

// RawArchive stores the raw ingested payloads for audit and replay.
type RawArchive interface {
	SaveTick(ctx context.Context, tenantID string, tick domain.Tick) error
}

// CandleStore persists finalized candles for the analytics read side.
type CandleStore interface {
	// SaveCandles upserts a batch. The write must be idempotent so a redelivery
	// converges rather than duplicating rows.
	SaveCandles(ctx context.Context, tenantID string, candles []domain.Candle) error
}

// EventPublisher emits domain events for downstream consumers (alert-service).
type EventPublisher interface {
	Publish(ctx context.Context, key string, value any) error
}
