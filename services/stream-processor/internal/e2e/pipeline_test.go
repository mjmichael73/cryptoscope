// Package e2e provides end-to-end pipeline tests for the cryptoscope data path.
//
// These tests validate the full ingest → aggregate → persist → query flow
// without requiring any external infrastructure. Each component is wired
// together using in-memory fakes so the tests run fast and stay deterministic.
//
// Run with:  go test ./tests/e2e/... -count=1 -v
// Or via the Makefile: make test-e2e
package e2e

import (
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"testing"

	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/aggregate"
	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/domain"
	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/etl"
)

// ---------------------------------------------------------------------------
// In-memory fakes for the store interfaces
// ---------------------------------------------------------------------------

type memArchive struct {
	ticks []domain.Tick
}

func (m *memArchive) SaveTick(_ context.Context, _ string, tick domain.Tick) error {
	m.ticks = append(m.ticks, tick)
	return nil
}

type memCandleStore struct {
	candles []domain.Candle
}

func (m *memCandleStore) SaveCandles(_ context.Context, _ string, candles []domain.Candle) error {
	m.candles = append(m.candles, candles...)
	return nil
}

type memEventPublisher struct {
	events []domain.CandleUpdatedEvent
}

func (m *memEventPublisher) Publish(_ context.Context, _ string, value any) error {
	if evt, ok := value.(domain.CandleUpdatedEvent); ok {
		m.events = append(m.events, evt)
	}
	return nil
}

// ---------------------------------------------------------------------------
// Pipeline wiring helper
// ---------------------------------------------------------------------------

type pipeline struct {
	archive   *memArchive
	candles   *memCandleStore
	publisher *memEventPublisher
	processor *etl.Processor
}

func newPipeline(intervals []string) *pipeline {
	archive := &memArchive{}
	candles := &memCandleStore{}
	publisher := &memEventPublisher{}
	agg := aggregate.New(intervals)
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	proc := etl.New(agg, archive, candles, publisher, "domain.events", "tenant-1", logger)
	return &pipeline{
		archive:   archive,
		candles:   candles,
		publisher: publisher,
		processor: proc,
	}
}

func (p *pipeline) sendTick(symbol string, price, volume float64, tsMillis int64) error {
	tick := domain.Tick{
		Symbol:   symbol,
		Price:    price,
		Volume:   volume,
		Source:   "binance",
		TsMillis: tsMillis,
	}
	b, _ := json.Marshal(tick)
	return p.processor.Handle(context.Background(), b)
}

func (p *pipeline) flush() error {
	return p.processor.Flush(context.Background())
}

// ---------------------------------------------------------------------------
// E2E Tests
// ---------------------------------------------------------------------------

// TestE2E_SingleSymbolSingleInterval validates the basic happy path:
// ingest several ticks, verify OHLC correctness, event publication, and
// that the archive captured every raw tick.
func TestE2E_SingleSymbolSingleInterval(t *testing.T) {
	p := newPipeline([]string{"1m"})

	// Simulate 5 ticks for BTCUSDT in the same 1m bucket.
	ticks := []struct {
		price float64
		vol   float64
		ts    int64
	}{
		{100, 1.0, 0},
		{105, 2.0, 10_000},
		{95, 1.5, 20_000},
		{110, 3.0, 30_000},
		{108, 0.5, 45_000},
	}

	for _, tk := range ticks {
		if err := p.sendTick("BTCUSDT", tk.price, tk.vol, tk.ts); err != nil {
			t.Fatalf("send tick: %v", err)
		}
	}

	// All 5 ticks archived.
	if len(p.archive.ticks) != 5 {
		t.Fatalf("expected 5 archived ticks, got %d", len(p.archive.ticks))
	}

	// No candle closed yet (all in bucket 0).
	if len(p.candles.candles) != 0 {
		t.Fatalf("expected 0 persisted candles, got %d", len(p.candles.candles))
	}
	if len(p.publisher.events) != 0 {
		t.Fatalf("expected 0 events, got %d", len(p.publisher.events))
	}

	// Flush to get the open candle.
	if err := p.flush(); err != nil {
		t.Fatalf("flush: %v", err)
	}
	if len(p.candles.candles) != 1 {
		t.Fatalf("expected 1 flushed candle, got %d", len(p.candles.candles))
	}

	c := p.candles.candles[0]
	if c.Open != 100 || c.High != 110 || c.Low != 95 || c.Close != 108 {
		t.Fatalf("OHLC mismatch: got O=%v H=%v L=%v C=%v", c.Open, c.High, c.Low, c.Close)
	}
	if c.Volume != 8.0 {
		t.Fatalf("volume: want 8.0, got %v", c.Volume)
	}
	if c.TradeCount != 5 {
		t.Fatalf("trade_count: want 5, got %d", c.TradeCount)
	}
	if c.Symbol != "BTCUSDT" || c.Interval != "1m" {
		t.Fatalf("symbol/interval: got %s/%s", c.Symbol, c.Interval)
	}
}

// TestE2E_BucketRolloverProducesClosedCandleAndEvent validates that a tick
// crossing a bucket boundary closes the current candle, persists it, and
// publishes a candle_updated event.
func TestE2E_BucketRolloverProducesClosedCandleAndEvent(t *testing.T) {
	p := newPipeline([]string{"1m"})

	// Two ticks: first in bucket 0, second in bucket 60000.
	if err := p.sendTick("ETHUSDT", 2000, 1.0, 30_000); err != nil {
		t.Fatal(err)
	}
	if err := p.sendTick("ETHUSDT", 2100, 1.0, 65_000); err != nil {
		t.Fatal(err)
	}

	// The rollover should have closed and persisted one candle.
	if len(p.candles.candles) != 1 {
		t.Fatalf("expected 1 persisted candle, got %d", len(p.candles.candles))
	}
	if len(p.publisher.events) != 1 {
		t.Fatalf("expected 1 event, got %d", len(p.publisher.events))
	}

	c := p.candles.candles[0]
	if c.Symbol != "ETHUSDT" {
		t.Fatalf("expected ETHUSDT, got %s", c.Symbol)
	}
	if c.Open != 2000 || c.Close != 2000 {
		t.Fatalf("OHLC: got O=%v C=%v", c.Open, c.Close)
	}
	if c.OpenTimeMs != 0 {
		t.Fatalf("open_time_ms: want 0, got %d", c.OpenTimeMs)
	}

	evt := p.publisher.events[0]
	if evt.EventType != "candle_updated" {
		t.Fatalf("event type: want candle_updated, got %s", evt.EventType)
	}
	if evt.TenantID != "tenant-1" {
		t.Fatalf("tenant: want tenant-1, got %s", evt.TenantID)
	}
	if evt.AggregateID != "ETHUSDT:1m:0" {
		t.Fatalf("aggregate_id: want ETHUSDT:1m:0, got %s", evt.AggregateID)
	}
}

// TestE2E_MultiSymbolIndependentAggregation verifies that ticks for different
// symbols maintain independent candle state.
func TestE2E_MultiSymbolIndependentAggregation(t *testing.T) {
	p := newPipeline([]string{"1m"})

	// Open candles for both symbols.
	if err := p.sendTick("BTCUSDT", 100, 1.0, 0); err != nil {
		t.Fatal(err)
	}
	if err := p.sendTick("ETHUSDT", 2000, 1.0, 0); err != nil {
		t.Fatal(err)
	}

	// Roll over BTCUSDT only.
	if err := p.sendTick("BTCUSDT", 110, 1.0, 65_000); err != nil {
		t.Fatal(err)
	}

	if len(p.candles.candles) != 1 {
		t.Fatalf("expected 1 persisted candle (BTC only), got %d", len(p.candles.candles))
	}
	if p.candles.candles[0].Symbol != "BTCUSDT" {
		t.Fatalf("expected BTCUSDT, got %s", p.candles.candles[0].Symbol)
	}

	// Flush should produce the BTC open candle and the ETH open candle.
	if err := p.flush(); err != nil {
		t.Fatal(err)
	}
	if len(p.candles.candles) != 3 { // 1 closed + 2 flushed
		t.Fatalf("expected 3 total candles after flush, got %d", len(p.candles.candles))
	}
}

// TestE2E_MultipleIntervalsClosesAllOnBoundary verifies that a tick crossing
// a 1h boundary closes both the 1m and 1h candles.
func TestE2E_MultipleIntervalsClosesAllOnBoundary(t *testing.T) {
	p := newPipeline([]string{"1m", "1h"})

	if err := p.sendTick("BTCUSDT", 100, 1.0, 0); err != nil {
		t.Fatal(err)
	}
	// Tick at the 1h boundary closes both 1m and 1h candles.
	if err := p.sendTick("BTCUSDT", 200, 1.0, 3_600_000); err != nil {
		t.Fatal(err)
	}

	if len(p.candles.candles) != 2 {
		t.Fatalf("expected 2 persisted candles (1m + 1h), got %d", len(p.candles.candles))
	}
	if len(p.publisher.events) != 2 {
		t.Fatalf("expected 2 events, got %d", len(p.publisher.events))
	}

	intervals := map[string]bool{"1m": false, "1h": false}
	for _, c := range p.candles.candles {
		intervals[c.Interval] = true
	}
	for iv, seen := range intervals {
		if !seen {
			t.Fatalf("interval %s not represented in persisted candles", iv)
		}
	}
}

// TestE2E_MalformedTickIsSkipped verifies that a malformed JSON tick does not
// crash the pipeline and the next valid tick is processed normally.
func TestE2E_MalformedTickIsSkipped(t *testing.T) {
	p := newPipeline([]string{"1m"})

	if err := p.processor.Handle(context.Background(), []byte("{bad json")); err != nil {
		t.Fatalf("malformed tick should not error: %v", err)
	}

	// Next tick processes fine.
	if err := p.sendTick("BTCUSDT", 100, 1.0, 0); err != nil {
		t.Fatal(err)
	}
	if err := p.flush(); err != nil {
		t.Fatal(err)
	}
	if len(p.candles.candles) != 1 {
		t.Fatalf("expected 1 candle after recovery, got %d", len(p.candles.candles))
	}
}

// TestE2E_VolumeAggregationAcrossTicks verifies that volume sums correctly
// across many ticks within a bucket.
func TestE2E_VolumeAggregationAcrossTicks(t *testing.T) {
	p := newPipeline([]string{"5m"})

	volumes := []float64{0.1, 0.2, 0.3, 0.4, 0.5, 1.0, 2.0}
	var total float64
	for i, v := range volumes {
		total += v
		if err := p.sendTick("SOLUSDT", 50.0+float64(i), v, int64(i*10_000)); err != nil {
			t.Fatal(err)
		}
	}

	if err := p.flush(); err != nil {
		t.Fatal(err)
	}
	if len(p.candles.candles) != 1 {
		t.Fatalf("expected 1 candle, got %d", len(p.candles.candles))
	}
	if p.candles.candles[0].Volume != total {
		t.Fatalf("volume: want %v, got %v", total, p.candles.candles[0].Volume)
	}
	if p.candles.candles[0].TradeCount != int64(len(volumes)) {
		t.Fatalf("trade_count: want %d, got %d", len(volumes), p.candles.candles[0].TradeCount)
	}
}

// TestE2E_ConsecutiveRollovers simulates a long-running session with many
// bucket transitions, verifying the correct number of candles close.
func TestE2E_ConsecutiveRollovers(t *testing.T) {
	p := newPipeline([]string{"1m"})

	// 10 ticks, one per 1m bucket → 9 rollovers → 9 closed candles.
	for i := 0; i < 10; i++ {
		ts := int64(i * 60_000)
		if err := p.sendTick("BTCUSDT", float64(100+i), 1.0, ts); err != nil {
			t.Fatal(err)
		}
	}

	if len(p.candles.candles) != 9 {
		t.Fatalf("expected 9 closed candles, got %d", len(p.candles.candles))
	}
	if len(p.publisher.events) != 9 {
		t.Fatalf("expected 9 events, got %d", len(p.publisher.events))
	}

	// Verify first closed candle.
	first := p.candles.candles[0]
	if first.Open != 100 || first.Close != 100 || first.OpenTimeMs != 0 {
		t.Fatalf("first candle: got O=%v C=%v bucket=%d", first.Open, first.Close, first.OpenTimeMs)
	}

	// Verify last closed candle (bucket = 8 * 60000 = 480000).
	// The 10th tick at ts=540k opens bucket 540k but never closes it.
	last := p.candles.candles[8]
	if last.Open != 108 || last.Close != 108 || last.OpenTimeMs != 480_000 {
		t.Fatalf("last candle: got O=%v C=%v bucket=%d", last.Open, last.Close, last.OpenTimeMs)
	}
}
