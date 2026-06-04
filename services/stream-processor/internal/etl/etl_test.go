package etl

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"testing"

	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/aggregate"
	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/domain"
)

type fakeArchive struct {
	saved []domain.Tick
	err   error
}

func (f *fakeArchive) SaveTick(_ context.Context, _ string, tick domain.Tick) error {
	if f.err != nil {
		return f.err
	}
	f.saved = append(f.saved, tick)
	return nil
}

type fakeCandles struct {
	saved []domain.Candle
	err   error
}

func (f *fakeCandles) SaveCandles(_ context.Context, _ string, candles []domain.Candle) error {
	if f.err != nil {
		return f.err
	}
	f.saved = append(f.saved, candles...)
	return nil
}

func newProcessor(archive *fakeArchive, candles *fakeCandles) *Processor {
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	return New(aggregate.New([]string{"1m"}), archive, candles, "tenant-1", logger)
}

func payload(t *testing.T, tick domain.Tick) []byte {
	t.Helper()
	b, err := json.Marshal(tick)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	return b
}

func TestHandleArchivesAndAggregates(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	proc := newProcessor(archive, candles)

	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 100, Volume: 1, TsMillis: 0})); err != nil {
		t.Fatalf("handle: %v", err)
	}
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 200, Volume: 1, TsMillis: 65_000})); err != nil {
		t.Fatalf("handle: %v", err)
	}

	if len(archive.saved) != 2 {
		t.Fatalf("expected 2 archived ticks, got %d", len(archive.saved))
	}
	if len(candles.saved) != 1 {
		t.Fatalf("expected 1 closed candle persisted, got %d", len(candles.saved))
	}
}

func TestHandleDropsMalformedPayload(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	proc := newProcessor(archive, candles)

	if err := proc.Handle(context.Background(), []byte("{not json")); err != nil {
		t.Fatalf("malformed payload should not error, got %v", err)
	}
	if len(archive.saved) != 0 {
		t.Fatalf("malformed payload should not be archived")
	}
}

func TestHandleReturnsErrorWhenArchiveFails(t *testing.T) {
	archive := &fakeArchive{err: errors.New("boom")}
	candles := &fakeCandles{}
	proc := newProcessor(archive, candles)

	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 1, TsMillis: 0})); err == nil {
		t.Fatal("expected error when archive fails")
	}
}

func TestFlushPersistsOpenCandles(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	proc := newProcessor(archive, candles)

	_ = proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 100, Volume: 1, TsMillis: 0}))
	if err := proc.Flush(context.Background()); err != nil {
		t.Fatalf("flush: %v", err)
	}
	if len(candles.saved) != 1 {
		t.Fatalf("expected flushed candle, got %d", len(candles.saved))
	}
}
