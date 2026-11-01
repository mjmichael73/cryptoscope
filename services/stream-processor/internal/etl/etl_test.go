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

// ---------------------------------------------------------------------------
// Fakes
// ---------------------------------------------------------------------------

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

func newProcessorIntervals(archive *fakeArchive, candles *fakeCandles, publisher *fakePublisher, intervals []string) *Processor {
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	return New(aggregate.New(intervals), archive, candles, publisher, "domain.events", "tenant-1", logger)
}

func payload(t *testing.T, tick domain.Tick) []byte {
	t.Helper()
	b, err := json.Marshal(tick)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	return b
}

// ---------------------------------------------------------------------------
// Basic Handle flow
// ---------------------------------------------------------------------------

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

func TestHandleEmptyPayload(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	proc := newProcessor(archive, candles, &fakePublisher{})

	// Empty JSON object — valid but with zero values.
	if err := proc.Handle(context.Background(), []byte(`{}`)); err != nil {
		t.Fatalf("empty payload should not error, got %v", err)
	}
	if len(archive.saved) != 1 {
		t.Fatalf("expected empty payload to be archived, got %d", len(archive.saved))
	}
}

// ---------------------------------------------------------------------------
// Error propagation
// ---------------------------------------------------------------------------

func TestHandleReturnsErrorWhenArchiveFails(t *testing.T) {
	archive := &fakeArchive{err: errors.New("boom")}
	candles := &fakeCandles{}
	proc := newProcessor(archive, candles, &fakePublisher{})

	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 1, TsMillis: 0})); err == nil {
		t.Fatal("expected error when archive fails")
	}
}

func TestHandleReturnsErrorWhenCandleStoreFails(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{err: errors.New("clickhouse down")}
	proc := newProcessor(archive, candles, &fakePublisher{})

	// First tick opens a candle.
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 100, Volume: 1, TsMillis: 0})); err != nil {
		t.Fatalf("handle: %v", err)
	}
	// Second tick closes a candle — candle store fails.
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 200, Volume: 1, TsMillis: 65_000})); err == nil {
		t.Fatal("expected error when candle store fails on rollover")
	}
	// Archive should still have both ticks.
	if len(archive.saved) != 2 {
		t.Fatalf("expected 2 archived ticks, got %d", len(archive.saved))
	}
}

func TestHandleReturnsErrorWhenPublisherFails(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	publisher := &fakePublisher{err: errors.New("kafka down")}
	proc := newProcessor(archive, candles, publisher)

	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 100, Volume: 1, TsMillis: 0})); err != nil {
		t.Fatalf("handle: %v", err)
	}
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 200, Volume: 1, TsMillis: 65_000})); err == nil {
		t.Fatal("expected error when publisher fails")
	}
	// Candles should still be persisted even though publishing failed.
	if len(candles.saved) != 1 {
		t.Fatalf("expected 1 saved candle despite publisher error, got %d", len(candles.saved))
	}
}

// ---------------------------------------------------------------------------
// Flush
// ---------------------------------------------------------------------------

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

func TestFlushReturnsNilWhenNothingOpen(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	proc := newProcessor(archive, candles, &fakePublisher{})

	if err := proc.Flush(context.Background()); err != nil {
		t.Fatalf("flush on empty processor should not error, got %v", err)
	}
	if len(candles.saved) != 0 {
		t.Fatalf("flush on empty processor should not save candles, got %d", len(candles.saved))
	}
}

func TestFlushReturnsErrorWhenCandleStoreFails(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{err: errors.New("flush failed")}
	proc := newProcessor(archive, candles, &fakePublisher{})

	_ = proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 100, Volume: 1, TsMillis: 0}))
	if err := proc.Flush(context.Background()); err == nil {
		t.Fatal("expected error when flush candle store fails")
	}
}

// ---------------------------------------------------------------------------
// Multi-interval ETL
// ---------------------------------------------------------------------------

func TestHandleMultiIntervalClosesMultipleCandles(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	publisher := &fakePublisher{}
	proc := newProcessorIntervals(archive, candles, publisher, []string{"1m", "1h"})

	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 100, Volume: 1, TsMillis: 0})); err != nil {
		t.Fatalf("handle 1: %v", err)
	}
	// Tick at 1h boundary closes both 1m and 1h candles.
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 200, Volume: 1, TsMillis: 3_600_000})); err != nil {
		t.Fatalf("handle 2: %v", err)
	}

	if len(candles.saved) != 2 {
		t.Fatalf("expected 2 saved candles (1m + 1h), got %d", len(candles.saved))
	}
	if len(publisher.published) != 2 {
		t.Fatalf("expected 2 published events, got %d", len(publisher.published))
	}

	intervals := map[string]bool{"1m": false, "1h": false}
	for _, c := range candles.saved {
		intervals[c.Interval] = true
	}
	for iv, seen := range intervals {
		if !seen {
			t.Fatalf("interval %s not in saved candles", iv)
		}
	}
}

// ---------------------------------------------------------------------------
// Event publishing details
// ---------------------------------------------------------------------------

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

func TestHandleEventTimestampEqualsBucketEnd(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	publisher := &fakePublisher{}
	proc := newProcessor(archive, candles, publisher)

	// Bucket 0 for 1m = [0, 60 000). Event timestamp should be 60 000.
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 100, Volume: 1, TsMillis: 0})); err != nil {
		t.Fatalf("handle 1: %v", err)
	}
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 200, Volume: 1, TsMillis: 65_000})); err != nil {
		t.Fatalf("handle 2: %v", err)
	}

	if len(publisher.published) != 1 {
		t.Fatalf("expected 1 event, got %d", len(publisher.published))
	}
	wantTS := int64(60_000) // open_time(0) + interval_width(60 000)
	if publisher.published[0].Timestamp != wantTS {
		t.Fatalf("event timestamp: want %d, got %d", wantTS, publisher.published[0].Timestamp)
	}
}

func TestHandleEventAggregateIDFormat(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	publisher := &fakePublisher{}
	proc := newProcessor(archive, candles, publisher)

	// Bucket 60 000 for 1m.
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "ETHUSDT", Price: 10, Volume: 1, TsMillis: 65_000})); err != nil {
		t.Fatalf("handle: %v", err)
	}
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "ETHUSDT", Price: 20, Volume: 1, TsMillis: 125_000})); err != nil {
		t.Fatalf("handle: %v", err)
	}

	wantID := "ETHUSDT:1m:60000"
	if publisher.published[0].AggregateID != wantID {
		t.Fatalf("aggregate_id: want %s, got %s", wantID, publisher.published[0].AggregateID)
	}
}

// ---------------------------------------------------------------------------
// Multi-symbol ETL
// ---------------------------------------------------------------------------

func TestHandleMultiSymbolIndependently(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	publisher := &fakePublisher{}
	proc := newProcessor(archive, candles, publisher)

	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 100, Volume: 1, TsMillis: 0})); err != nil {
		t.Fatalf("handle btc 1: %v", err)
	}
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "ETHUSDT", Price: 10, Volume: 1, TsMillis: 0})); err != nil {
		t.Fatalf("handle eth 1: %v", err)
	}
	// Only BTCUSDT rolls over.
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 200, Volume: 1, TsMillis: 65_000})); err != nil {
		t.Fatalf("handle btc 2: %v", err)
	}

	if len(candles.saved) != 1 {
		t.Fatalf("expected 1 saved candle (only BTC), got %d", len(candles.saved))
	}
	if candles.saved[0].Symbol != "BTCUSDT" {
		t.Fatalf("expected BTCUSDT, got %s", candles.saved[0].Symbol)
	}
	if len(publisher.published) != 1 {
		t.Fatalf("expected 1 event, got %d", len(publisher.published))
	}
}

func TestHandleMultiSymbolBothRollOver(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	publisher := &fakePublisher{}
	proc := newProcessor(archive, candles, publisher)

	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 100, Volume: 1, TsMillis: 0})); err != nil {
		t.Fatalf("handle btc: %v", err)
	}
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "ETHUSDT", Price: 10, Volume: 1, TsMillis: 0})); err != nil {
		t.Fatalf("handle eth: %v", err)
	}
	// Both roll over.
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 200, Volume: 1, TsMillis: 65_000})); err != nil {
		t.Fatalf("handle btc 2: %v", err)
	}
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "ETHUSDT", Price: 20, Volume: 1, TsMillis: 65_000})); err != nil {
		t.Fatalf("handle eth 2: %v", err)
	}

	if len(candles.saved) != 2 {
		t.Fatalf("expected 2 saved candles, got %d", len(candles.saved))
	}
	if len(publisher.published) != 2 {
		t.Fatalf("expected 2 events, got %d", len(publisher.published))
	}
}

// ---------------------------------------------------------------------------
// Consecutive rollovers (long tick history)
// ---------------------------------------------------------------------------

func TestHandleConsecutiveRollovers(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	publisher := &fakePublisher{}
	proc := newProcessor(archive, candles, publisher)

	// Five ticks spanning five consecutive 1m buckets.
	timestamps := []int64{0, 65_000, 125_000, 185_000, 245_000}
	for i, ts := range timestamps {
		if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: float64(100 + i), Volume: 1, TsMillis: ts})); err != nil {
			t.Fatalf("handle %d: %v", i, err)
		}
	}

	// 4 rollovers → 4 closed candles + 1 open.
	if len(candles.saved) != 4 {
		t.Fatalf("expected 4 saved candles, got %d", len(candles.saved))
	}
	if len(publisher.published) != 4 {
		t.Fatalf("expected 4 events, got %d", len(publisher.published))
	}

	// All archived.
	if len(archive.saved) != 5 {
		t.Fatalf("expected 5 archived ticks, got %d", len(archive.saved))
	}
}

// ---------------------------------------------------------------------------
// Malformed payload does not skip subsequent ticks
// ---------------------------------------------------------------------------

func TestHandleMalformedPayloadThenValid(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	proc := newProcessor(archive, candles, &fakePublisher{})

	// Malformed.
	_ = proc.Handle(context.Background(), []byte("{bad"))
	// Valid.
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 100, Volume: 1, TsMillis: 0})); err != nil {
		t.Fatalf("handle after malformed: %v", err)
	}

	if len(archive.saved) != 1 {
		t.Fatalf("expected 1 archived tick after malformed payload, got %d", len(archive.saved))
	}
}

// ---------------------------------------------------------------------------
// Empty intervals list
// ---------------------------------------------------------------------------

func TestHandleWithEmptyIntervals(t *testing.T) {
	archive := &fakeArchive{}
	candles := &fakeCandles{}
	proc := newProcessorIntervals(archive, candles, &fakePublisher{}, []string{})

	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 100, Volume: 1, TsMillis: 0})); err != nil {
		t.Fatalf("handle: %v", err)
	}
	if err := proc.Handle(context.Background(), payload(t, domain.Tick{Symbol: "BTCUSDT", Price: 200, Volume: 1, TsMillis: 65_000})); err != nil {
		t.Fatalf("handle: %v", err)
	}

	// No candles should be closed or saved.
	if len(candles.saved) != 0 {
		t.Fatalf("expected 0 saved candles with empty intervals, got %d", len(candles.saved))
	}
}
