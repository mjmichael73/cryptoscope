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

type fakePublisher struct {
	published []domain.CandleUpdatedEvent
	err       error
}

func (f *fakePublisher) Publish(_ context.Context, _ string, value any) error {
	if f.err != nil {
		return f.err
	}
	event, ok := value.(domain.CandleUpdatedEvent)
	if ok {
		f.published = append(f.published, event)
	}
	return nil
}

func newProcessor(archive *fakeArchive, candles *fakeCandles, publisher *fakePublisher) *Processor {
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	return New(aggregate.New([]string{"1m"}), archive, candles, publisher, "domain.events", "tenant-1", logger)
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
	proc := newProcessor(archive, candles, &fakePublisher{})

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
	proc := newProcessor(archive, candles, &fakePublisher{})

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
	proc := newProcessor(archive, candles, &fakePublisher{})

	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 1, TsMillis: 0})); err == nil {
		t.Fatal("expected error when archive fails")
	}
}

func TestFlushPersistsOpenCandles(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	proc := newProcessor(archive, candles, &fakePublisher{})

	_ = proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 100, Volume: 1, TsMillis: 0}))
	if err := proc.Flush(context.Background()); err != nil {
		t.Fatalf("flush: %v", err)
	}
	if len(candles.saved) != 1 {
		t.Fatalf("expected flushed candle, got %d", len(candles.saved))
	}
}

func TestHandlePublishesCandleUpdatedEvent(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	publisher := &fakePublisher{}
	proc := newProcessor(archive, candles, publisher)

	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 100, Volume: 1, TsMillis: 0})); err != nil {
		t.Fatalf("handle 1: %v", err)
	}
	if len(publisher.published) != 0 {
		t.Fatalf("expected no events on first tick, got %d", len(publisher.published))
	}

	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 200, Volume: 1, TsMillis: 65_000})); err != nil {
		t.Fatalf("handle 2: %v", err)
	}
	if len(publisher.published) != 1 {
		t.Fatalf("expected 1 candle_updated event, got %d", len(publisher.published))
	}

	event := publisher.published[0]
	if event.EventType != "candle_updated" {
		t.Fatalf("expected event_type candle_updated, got %s", event.EventType)
	}
	if event.TenantID != "tenant-1" {
		t.Fatalf("expected tenant-1, got %s", event.TenantID)
	}
	if event.Data.Symbol != "BTCUSDT" {
		t.Fatalf("expected symbol BTCUSDT, got %s", event.Data.Symbol)
	}
	if event.Data.Close != 100 {
		t.Fatalf("expected close 100, got %v", event.Data.Close)
	}
	if event.AggregateID != "BTCUSDT:1m:0" {
		t.Fatalf("expected aggregate_id BTCUSDT:1m:0, got %s", event.AggregateID)
	}
}

func TestHandlePublishesEventForEveryClosedInterval(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	publisher := &fakePublisher{}
	proc := newProcessor(archive, candles, publisher)

	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "ETHUSDT", Price: 10, Volume: 1, TsMillis: 0})); err != nil {
		t.Fatalf("handle 1: %v", err)
	}
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "ETHUSDT", Price: 20, Volume: 1, TsMillis: 65_000})); err != nil {
		t.Fatalf("handle 2: %v", err)
	}

	if len(publisher.published) != 1 {
		t.Fatalf("expected 1 published event, got %d", len(publisher.published))
	}
}
