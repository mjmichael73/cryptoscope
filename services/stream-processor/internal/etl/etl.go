// Package etl ties the consumer, aggregator, and stores together.
//
// The flow is deliberately simple: read a tick, archive it, fold it into the
// aggregator, and persist any candles the tick closed. Offsets are committed
// only after the work is durable, which keeps processing at-least-once.
package etl

import (
	"context"
	"encoding/json"
	"log/slog"

	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/aggregate"
	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/domain"
	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/store"
)

// Processor folds ticks into candles and persists both sides.
type Processor struct {
	aggregator *aggregate.Aggregator
	archive    store.RawArchive
	candles    store.CandleStore
	tenantID   string
	logger     *slog.Logger
}

// New builds a Processor. The tenant id is passed in because, in this
// single-tenant ingestion path, every tick belongs to the platform tenant;
// per-tenant routing lives at the gateway.
func New(agg *aggregate.Aggregator, archive store.RawArchive, candles store.CandleStore, tenantID string, logger *slog.Logger) *Processor {
	return &Processor{
		aggregator: agg,
		archive:    archive,
		candles:    candles,
		tenantID:   tenantID,
		logger:     logger,
	}
}

// Handle processes a single raw Kafka payload. It returns an error when the
// work is not durable so the caller can avoid committing the offset.
func (p *Processor) Handle(ctx context.Context, payload []byte) error {
	var tick domain.Tick
	if err := json.Unmarshal(payload, &tick); err != nil {
		// A malformed message will never succeed on retry, so we log and drop
		// it rather than blocking the partition.
		p.logger.Warn("dropping malformed tick", slog.String("error", err.Error()))
		return nil
	}

	if err := p.archive.SaveTick(ctx, p.tenantID, tick); err != nil {
		return err
	}

	closed := p.aggregator.Add(tick)
	if len(closed) == 0 {
		return nil
	}
	return p.candles.SaveCandles(ctx, p.tenantID, closed)
}

// Flush persists any open candles. Call it on shutdown.
func (p *Processor) Flush(ctx context.Context) error {
	closed := p.aggregator.Flush()
	if len(closed) == 0 {
		return nil
	}
	return p.candles.SaveCandles(ctx, p.tenantID, closed)
}
