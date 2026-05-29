package pipeline

import (
	"context"
	"errors"
	"io"
	"log/slog"
	"testing"

	"github.com/mojimich2015/cryptoscope/services/ingest-service/internal/domain"
)

type fakeDeduper struct {
	seen map[string]bool
	err  error
}

func (f *fakeDeduper) FirstSeen(_ context.Context, key string) (bool, error) {
	if f.err != nil {
		return false, f.err
	}
	if f.seen[key] {
		return false, nil
	}
	f.seen[key] = true
	return true, nil
}

type fakePublisher struct {
	published []domain.Tick
	err       error
}

func (f *fakePublisher) Publish(_ context.Context, _ string, value any) error {
	if f.err != nil {
		return f.err
	}
	f.published = append(f.published, value.(domain.Tick))
	return nil
}

func testLogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(io.Discard, nil))
}

func TestProcessPublishesValidTicksOnce(t *testing.T) {
	deduper := &fakeDeduper{seen: map[string]bool{}}
	publisher := &fakePublisher{}
	p := New(deduper, publisher, testLogger())

	tick := domain.Tick{Symbol: "BTCUSDT", Price: 1, Source: "binance", TsMillis: 1_700_000_000_000}
	batch := []domain.Tick{tick, tick} // the second is a duplicate

	result, err := p.Process(context.Background(), batch)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Published != 1 || result.Skipped != 1 {
		t.Fatalf("expected 1 published and 1 skipped, got %+v", result)
	}
	if len(publisher.published) != 1 {
		t.Fatalf("expected 1 message published, got %d", len(publisher.published))
	}
}

func TestProcessCountsInvalidTicks(t *testing.T) {
	p := New(&fakeDeduper{seen: map[string]bool{}}, &fakePublisher{}, testLogger())
	batch := []domain.Tick{{Symbol: "", Price: 0}}
	result, err := p.Process(context.Background(), batch)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Invalid != 1 || result.Published != 0 {
		t.Fatalf("expected 1 invalid and 0 published, got %+v", result)
	}
}

func TestProcessReturnsPublishError(t *testing.T) {
	publisher := &fakePublisher{err: errors.New("broker down")}
	p := New(&fakeDeduper{seen: map[string]bool{}}, publisher, testLogger())
	tick := domain.Tick{Symbol: "BTCUSDT", Price: 1, Source: "binance", TsMillis: 1}
	if _, err := p.Process(context.Background(), []domain.Tick{tick}); err == nil {
		t.Fatal("expected the publish error to propagate")
	}
}
