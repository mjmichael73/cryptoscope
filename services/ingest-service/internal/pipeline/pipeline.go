// Package pipeline turns fetched ticks into Kafka messages, dropping duplicates
// on the way. It is the heart of the ingest service.
package pipeline

import (
	"context"
	"log/slog"

	"github.com/mojimich2015/cryptoscope/services/ingest-service/internal/domain"
)

// Deduper reports whether a dedupe key is being seen for the first time.
type Deduper interface {
	FirstSeen(ctx context.Context, key string) (bool, error)
}

// Publisher sends a tick downstream, keyed by symbol so a symbol's ticks stay
// ordered within a partition.
type Publisher interface {
	Publish(ctx context.Context, key string, value any) error
}

// Pipeline validates, deduplicates, and publishes ticks.
type Pipeline struct {
	deduper   Deduper
	publisher Publisher
	logger    *slog.Logger
}

// New builds a Pipeline.
func New(deduper Deduper, publisher Publisher, logger *slog.Logger) *Pipeline {
	return &Pipeline{deduper: deduper, publisher: publisher, logger: logger}
}

// Result summarizes what happened to a batch of ticks.
type Result struct {
	Published int
	Skipped   int
	Invalid   int
}

// Process handles a batch of ticks. Invalid ticks are counted and dropped,
// duplicates are skipped, and the rest are published. A publish failure stops
// the batch and returns the error so the caller can retry.
func (p *Pipeline) Process(ctx context.Context, ticks []domain.Tick) (Result, error) {
	var result Result
	for _, tick := range ticks {
		if !tick.Valid() {
			result.Invalid++
			continue
		}

		first, err := p.deduper.FirstSeen(ctx, tick.DedupeKey())
		if err != nil {
			return result, err
		}
		if !first {
			result.Skipped++
			continue
		}

		if err := p.publisher.Publish(ctx, tick.Symbol, tick); err != nil {
			return result, err
		}
		result.Published++
	}

	p.logger.Info("processed tick batch",
		slog.Int("published", result.Published),
		slog.Int("skipped", result.Skipped),
		slog.Int("invalid", result.Invalid),
	)
	return result, nil
}
