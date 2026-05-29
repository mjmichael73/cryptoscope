package pipeline

import (
	"context"
	"log/slog"
	"time"

	"github.com/mojimich2015/cryptoscope/services/ingest-service/internal/source"
)

// Scheduler polls each source on a fixed interval and feeds the results into
// the pipeline. It is the top level loop of the service.
type Scheduler struct {
	sources  []source.Source
	symbols  []string
	interval time.Duration
	pipeline *Pipeline
	logger   *slog.Logger
}

// NewScheduler builds a Scheduler.
func NewScheduler(sources []source.Source, symbols []string, interval time.Duration, pipeline *Pipeline, logger *slog.Logger) *Scheduler {
	return &Scheduler{
		sources:  sources,
		symbols:  symbols,
		interval: interval,
		pipeline: pipeline,
		logger:   logger,
	}
}

// Run polls until the context is cancelled. Each tick of the timer polls every
// source; a failing source is logged and skipped rather than stopping the loop.
func (s *Scheduler) Run(ctx context.Context) error {
	ticker := time.NewTicker(s.interval)
	defer ticker.Stop()

	s.pollOnce(ctx)
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			s.pollOnce(ctx)
		}
	}
}

func (s *Scheduler) pollOnce(ctx context.Context) {
	for _, src := range s.sources {
		ticks, err := src.Fetch(ctx, s.symbols)
		if err != nil {
			s.logger.Warn("source fetch failed",
				slog.String("source", src.Name()),
				slog.String("error", err.Error()),
			)
			continue
		}
		if _, err := s.pipeline.Process(ctx, ticks); err != nil {
			s.logger.Error("pipeline process failed",
				slog.String("source", src.Name()),
				slog.String("error", err.Error()),
			)
		}
	}
}
