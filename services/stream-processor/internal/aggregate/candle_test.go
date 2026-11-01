package aggregate

import (
	"testing"

	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/domain"
)

func tick(symbol string, price, volume float64, ts int64) domain.Tick {
	return domain.Tick{Symbol: symbol, Price: price, Volume: volume, TsMillis: ts}
}

// ---------------------------------------------------------------------------
// OHLC within a single bucket
// ---------------------------------------------------------------------------

func TestAddBuildsOHLCWithinBucket(t *testing.T) {
	agg := New([]string{"1m"})

	if got := agg.Add(tick("BTCUSDT", 100, 1, 0)); len(got) != 0 {
		t.Fatalf("first tick should not close a candle, got %d", len(got))
	}
	agg.Add(tick("BTCUSDT", 120, 2, 10_000))
	agg.Add(tick("BTCUSDT", 90, 3, 20_000))
	agg.Add(tick("BTCUSDT", 110, 4, 30_000))

	candles := agg.Flush()
	if len(candles) != 1 {
		t.Fatalf("expected one open candle, got %d", len(candles))
	}
	c := candles[0]
	if c.Open != 100 || c.High != 120 || c.Low != 90 || c.Close != 110 {
		t.Fatalf("unexpected OHLC: %+v", c)
	}
	if c.Volume != 10 {
		t.Fatalf("expected volume 10, got %v", c.Volume)
	}
	if c.TradeCount != 4 {
		t.Fatalf("expected 4 trades, got %d", c.TradeCount)
	}
	if c.OpenTimeMs != 0 {
		t.Fatalf("expected bucket 0, got %d", c.OpenTimeMs)
	}
}

func TestAddReturnsNoCloseOnFirstTick(t *testing.T) {
	agg := New([]string{"1m"})
	closed := agg.Add(tick("BTCUSDT", 500, 0.5, 0))
	if len(closed) != 0 {
		t.Fatalf("first tick must not close a candle, got %d", len(closed))
	}
}

func TestAddReturnsNoCloseWithinSameBucket(t *testing.T) {
	agg := New([]string{"1m"})
	agg.Add(tick("BTCUSDT", 100, 1, 10_000))
	closed := agg.Add(tick("BTCUSDT", 200, 1, 59_000))
	if len(closed) != 0 {
		t.Fatalf("same-bucket tick should not close a candle, got %d", len(closed))
	}
}

// ---------------------------------------------------------------------------
// Bucket rollover
// ---------------------------------------------------------------------------

func TestAddClosesCandleOnBucketRollover(t *testing.T) {
	agg := New([]string{"1m"})

	agg.Add(tick("ETHUSDT", 10, 1, 30_000))
	closed := agg.Add(tick("ETHUSDT", 20, 1, 65_000))

	if len(closed) != 1 {
		t.Fatalf("expected one closed candle, got %d", len(closed))
	}
	if closed[0].Close != 10 || closed[0].OpenTimeMs != 0 {
		t.Fatalf("unexpected closed candle: %+v", closed[0])
	}

	remaining := agg.Flush()
	if len(remaining) != 1 || remaining[0].OpenTimeMs != 60_000 {
		t.Fatalf("expected new bucket at 60000, got %+v", remaining)
	}
}

func TestAddClosesOnTickAtBucketBoundary(t *testing.T) {
	agg := New([]string{"1m"})
	agg.Add(tick("BTCUSDT", 100, 1, 0))
	// Exactly at the boundary: 60 000 ms is the start of the next 1m bucket.
	closed := agg.Add(tick("BTCUSDT", 110, 1, 60_000))
	if len(closed) != 1 {
		t.Fatalf("expected candle to close at bucket boundary, got %d", len(closed))
	}
	if closed[0].OpenTimeMs != 0 {
		t.Fatalf("closed candle should be from bucket 0, got %d", closed[0].OpenTimeMs)
	}

	remaining := agg.Flush()
	if len(remaining) != 1 || remaining[0].OpenTimeMs != 60_000 {
		t.Fatalf("expected open candle at 60000, got %+v", remaining)
	}
}

func TestAddMultipleRolloversInSequence(t *testing.T) {
	agg := New([]string{"1m"})
	agg.Add(tick("BTCUSDT", 100, 1, 0))                  // bucket 0
	closed1 := agg.Add(tick("BTCUSDT", 110, 1, 65_000))  // bucket 60k
	closed2 := agg.Add(tick("BTCUSDT", 120, 1, 125_000)) // bucket 120k

	if len(closed1) != 1 {
		t.Fatalf("first rollover: expected 1 closed, got %d", len(closed1))
	}
	if closed1[0].OpenTimeMs != 0 {
		t.Fatalf("first closed candle bucket: want 0, got %d", closed1[0].OpenTimeMs)
	}

	if len(closed2) != 1 {
		t.Fatalf("second rollover: expected 1 closed, got %d", len(closed2))
	}
	if closed2[0].OpenTimeMs != 60_000 {
		t.Fatalf("second closed candle bucket: want 60000, got %d", closed2[0].OpenTimeMs)
	}

	remaining := agg.Flush()
	if len(remaining) != 1 || remaining[0].OpenTimeMs != 120_000 {
		t.Fatalf("expected open candle at 120000, got %+v", remaining)
	}
}

// ---------------------------------------------------------------------------
// Multiple intervals
// ---------------------------------------------------------------------------

func TestAddTracksMultipleIntervals(t *testing.T) {
	agg := New([]string{"1m", "5m"})

	agg.Add(tick("BTCUSDT", 100, 1, 0))
	closed := agg.Add(tick("BTCUSDT", 200, 1, 61_000))

	// The 1m bucket rolls over, the 5m one does not.
	if len(closed) != 1 {
		t.Fatalf("expected exactly one interval to close, got %d", len(closed))
	}
	if closed[0].Interval != "1m" {
		t.Fatalf("expected the 1m candle to close, got %s", closed[0].Interval)
	}
}

func TestAddClosesMultipleIntervalsSimultaneously(t *testing.T) {
	// Use 1m and 1h. A tick spanning the 1h boundary (3 600 000 ms) will
	// roll over both the 1m and 1h candles.
	agg := New([]string{"1m", "1h"})
	agg.Add(tick("BTCUSDT", 100, 1, 0))
	closed := agg.Add(tick("BTCUSDT", 200, 1, 3_600_000))

	if len(closed) != 2 {
		t.Fatalf("expected both 1m and 1h to close, got %d", len(closed))
	}

	intervals := map[string]bool{"1m": false, "1h": false}
	for _, c := range closed {
		intervals[c.Interval] = true
	}
	for iv, seen := range intervals {
		if !seen {
			t.Fatalf("interval %s should have closed but did not", iv)
		}
	}
}

func TestAdd5mInterval(t *testing.T) {
	agg := New([]string{"5m"})
	// 5m = 300 000 ms. Bucket 0 covers [0, 300 000).
	agg.Add(tick("BTCUSDT", 100, 1, 0))
	agg.Add(tick("BTCUSDT", 110, 1, 299_999))           // still bucket 0
	closed := agg.Add(tick("BTCUSDT", 120, 1, 300_000)) // bucket 300 000 — rollover

	if len(closed) != 1 {
		t.Fatalf("expected 5m candle to close, got %d", len(closed))
	}
	c := closed[0]
	if c.Interval != "5m" {
		t.Fatalf("expected interval 5m, got %s", c.Interval)
	}
	// Closed candle: O=100 (first tick), H=110 (tick 2), L=100, C=110 (tick 2, last in bucket)
	if c.Open != 100 || c.High != 110 || c.Low != 100 || c.Close != 110 {
		t.Fatalf("unexpected OHLC in 5m candle: %+v", c)
	}
	if c.TradeCount != 2 {
		t.Fatalf("expected 2 trades, got %d", c.TradeCount)
	}
}

func TestAdd1hInterval(t *testing.T) {
	agg := New([]string{"1h"})
	// 1h = 3 600 000 ms.
	agg.Add(tick("ETHUSDT", 50, 2, 0))
	agg.Add(tick("ETHUSDT", 55, 3, 3_599_999))           // same bucket as ts=0
	closed := agg.Add(tick("ETHUSDT", 60, 4, 3_600_000)) // bucket 3 600 000 — rollover

	if len(closed) != 1 {
		t.Fatalf("expected 1h candle to close, got %d", len(closed))
	}
	c := closed[0]
	if c.Interval != "1h" {
		t.Fatalf("expected interval 1h, got %s", c.Interval)
	}
	// Closed candle: O=50, H=55 (tick 2), L=50, C=55 (tick 2, last in bucket)
	if c.Open != 50 || c.High != 55 || c.Low != 50 || c.Close != 55 {
		t.Fatalf("unexpected OHLC in 1h candle: %+v", c)
	}
	if c.Volume != 5 {
		t.Fatalf("expected volume 5, got %v", c.Volume)
	}
}

func TestAdd1dInterval(t *testing.T) {
	agg := New([]string{"1d"})
	// 1d = 86 400 000 ms.
	agg.Add(tick("SOLUSDT", 20, 10, 0))
	closed := agg.Add(tick("SOLUSDT", 25, 5, 86_400_000))

	if len(closed) != 1 {
		t.Fatalf("expected 1d candle to close, got %d", len(closed))
	}
	c := closed[0]
	if c.Interval != "1d" {
		t.Fatalf("expected interval 1d, got %s", c.Interval)
	}
	if c.Open != 20 || c.Close != 20 {
		t.Fatalf("unexpected OHLC in 1d candle: %+v", c)
	}
	if c.TradeCount != 1 {
		t.Fatalf("expected 1 trade, got %d", c.TradeCount)
	}
}

// ---------------------------------------------------------------------------
// Multi-symbol isolation
// ---------------------------------------------------------------------------

func TestAddIsolatesSymbols(t *testing.T) {
	agg := New([]string{"1m"})
	agg.Add(tick("BTCUSDT", 100, 1, 0))
	agg.Add(tick("ETHUSDT", 10, 1, 0))

	// Roll over BTCUSDT only.
	closed := agg.Add(tick("BTCUSDT", 200, 1, 65_000))
	if len(closed) != 1 {
		t.Fatalf("expected 1 closed candle, got %d", len(closed))
	}
	if closed[0].Symbol != "BTCUSDT" {
		t.Fatalf("expected BTCUSDT, got %s", closed[0].Symbol)
	}

	// Flush returns both ETHUSDT's open candle and BTCUSDT's new open candle.
	remaining := agg.Flush()
	if len(remaining) != 2 {
		t.Fatalf("expected 2 open candles after flush, got %d", len(remaining))
	}
	symbols := map[string]bool{"BTCUSDT": false, "ETHUSDT": false}
	for _, c := range remaining {
		symbols[c.Symbol] = true
	}
	for s, seen := range symbols {
		if !seen {
			t.Fatalf("expected symbol %s in flush output", s)
		}
	}
}

func TestAddMultipleSymbolsCloseOnRollover(t *testing.T) {
	agg := New([]string{"1m"})
	agg.Add(tick("BTCUSDT", 100, 1, 0))
	agg.Add(tick("ETHUSDT", 10, 1, 0))

	// Both symbols roll over at 65 000.
	closedBTC := agg.Add(tick("BTCUSDT", 200, 1, 65_000))
	closedETH := agg.Add(tick("ETHUSDT", 20, 1, 65_000))

	if len(closedBTC) != 1 || closedBTC[0].Symbol != "BTCUSDT" {
		t.Fatalf("expected BTCUSDT candle to close, got %+v", closedBTC)
	}
	if len(closedETH) != 1 || closedETH[0].Symbol != "ETHUSDT" {
		t.Fatalf("expected ETHUSDT candle to close, got %+v", closedETH)
	}
}

// ---------------------------------------------------------------------------
// Edge cases
// ---------------------------------------------------------------------------

func TestAddZeroVolumeTick(t *testing.T) {
	agg := New([]string{"1m"})
	agg.Add(tick("BTCUSDT", 100, 0, 0))
	candles := agg.Flush()
	if len(candles) != 1 {
		t.Fatalf("expected 1 candle, got %d", len(candles))
	}
	if candles[0].Volume != 0 {
		t.Fatalf("expected volume 0, got %v", candles[0].Volume)
	}
	if candles[0].TradeCount != 1 {
		t.Fatalf("expected 1 trade, got %d", candles[0].TradeCount)
	}
}

func TestAddAllIdenticalPrices(t *testing.T) {
	agg := New([]string{"1m"})
	agg.Add(tick("BTCUSDT", 42, 1, 0))
	agg.Add(tick("BTCUSDT", 42, 1, 10_000))
	agg.Add(tick("BTCUSDT", 42, 1, 20_000))

	candles := agg.Flush()
	if len(candles) != 1 {
		t.Fatalf("expected 1 candle, got %d", len(candles))
	}
	c := candles[0]
	if c.Open != 42 || c.High != 42 || c.Low != 42 || c.Close != 42 {
		t.Fatalf("expected all 42s, got open=%v high=%v low=%v close=%v", c.Open, c.High, c.Low, c.Close)
	}
}

func TestAddNegativePrice(t *testing.T) {
	// Exchanges never send negative prices, but the aggregator should not
	// break if one slips through.
	agg := New([]string{"1m"})
	agg.Add(tick("BTCUSDT", -10, 1, 0))
	agg.Add(tick("BTCUSDT", -5, 1, 10_000))
	agg.Add(tick("BTCUSDT", -20, 1, 20_000))

	candles := agg.Flush()
	if len(candles) != 1 {
		t.Fatalf("expected 1 candle, got %d", len(candles))
	}
	c := candles[0]
	if c.Open != -10 || c.High != -5 || c.Low != -20 || c.Close != -20 {
		t.Fatalf("unexpected OHLC: %+v", c)
	}
}

func TestAddLargeTimestamps(t *testing.T) {
	agg := New([]string{"1m"})
	// A realistic timestamp aligned to a 60 000 ms boundary.
	base := int64(1_800_000_000_000) // 30M * 60k = 1.8T, perfectly aligned
	agg.Add(tick("BTCUSDT", 100, 1, base))
	closed := agg.Add(tick("BTCUSDT", 110, 1, base+60_000))
	if len(closed) != 1 {
		t.Fatalf("expected 1 closed candle, got %d", len(closed))
	}
	if closed[0].OpenTimeMs != base {
		t.Fatalf("expected bucket %d, got %d", base, closed[0].OpenTimeMs)
	}
}

// ---------------------------------------------------------------------------
// New / Flush basics
// ---------------------------------------------------------------------------

func TestNewIgnoresUnknownIntervals(t *testing.T) {
	agg := New([]string{"1m", "bogus"})
	agg.Add(tick("BTCUSDT", 100, 1, 0))
	if got := agg.Flush(); len(got) != 1 {
		t.Fatalf("unknown interval should be dropped, got %d candles", len(got))
	}
}

func TestNewEmptyIntervals(t *testing.T) {
	agg := New([]string{})
	agg.Add(tick("BTCUSDT", 100, 1, 0))
	if got := agg.Flush(); len(got) != 0 {
		t.Fatalf("empty intervals should produce no candles, got %d", len(got))
	}
}

func TestFlushReturnsNothingWhenEmpty(t *testing.T) {
	agg := New([]string{"1m"})
	got := agg.Flush()
	if len(got) != 0 {
		t.Fatalf("flush on empty aggregator should return nothing, got %d", len(got))
	}
}

func TestFlushClearsOpenCandles(t *testing.T) {
	agg := New([]string{"1m"})
	agg.Add(tick("BTCUSDT", 100, 1, 0))
	_ = agg.Flush()
	// Second flush should be empty.
	got := agg.Flush()
	if len(got) != 0 {
		t.Fatalf("second flush should return nothing, got %d", len(got))
	}
}

func TestFlushPreservesSymbolAndInterval(t *testing.T) {
	agg := New([]string{"5m", "1h"})
	agg.Add(tick("BTCUSDT", 100, 1, 0)) //nolint:errcheck // testing Flush output
	got := agg.Flush()
	if len(got) != 2 {
		t.Fatalf("expected 2 candles (5m + 1h), got %d", len(got))
	}
	seen := map[string]bool{"5m": false, "1h": false}
	for _, c := range got {
		if c.Symbol != "BTCUSDT" {
			t.Fatalf("expected symbol BTCUSDT, got %s", c.Symbol)
		}
		seen[c.Interval] = true
	}
	for iv, found := range seen {
		if !found {
			t.Fatalf("interval %s not found in flush output", iv)
		}
	}
}

// ---------------------------------------------------------------------------
// Table-driven: bucket boundaries across intervals
// ---------------------------------------------------------------------------

func TestBucketBoundaryTable(t *testing.T) {
	tests := []struct {
		name     string
		interval string
		width    int64
		ticks    []struct {
			price float64
			ts    int64
		}
		wantOpenMs int64
		wantClose  float64
	}{
		{
			name:     "1m boundary",
			interval: "1m",
			width:    60_000,
			ticks: []struct {
				price float64
				ts    int64
			}{
				{100, 0},
				{110, 30_000},
				{120, 60_000}, // rollover
			},
			wantOpenMs: 0,
			wantClose:  110,
		},
		{
			name:     "5m boundary",
			interval: "5m",
			width:    300_000,
			ticks: []struct {
				price float64
				ts    int64
			}{
				{200, 100_000},
				{210, 299_999},
				{220, 300_000}, // rollover
			},
			wantOpenMs: 0,
			wantClose:  210,
		},
		{
			name:     "1h boundary",
			interval: "1h",
			width:    3_600_000,
			ticks: []struct {
				price float64
				ts    int64
			}{
				{300, 0},
				{310, 3_599_999},
				{320, 3_600_000}, // rollover
			},
			wantOpenMs: 0,
			wantClose:  310,
		},
		{
			name:     "1d boundary",
			interval: "1d",
			width:    86_400_000,
			ticks: []struct {
				price float64
				ts    int64
			}{
				{400, 0},
				{410, 86_399_999},
				{420, 86_400_000}, // rollover
			},
			wantOpenMs: 0,
			wantClose:  410,
		},
		{
			name:     "non-zero start 1m",
			interval: "1m",
			width:    60_000,
			ticks: []struct {
				price float64
				ts    int64
			}{
				{100, 10_000},
				{110, 50_000},
				{120, 60_000}, // rollover
			},
			wantOpenMs: 0,
			wantClose:  110,
		},
		{
			name:     "offset bucket",
			interval: "5m",
			width:    300_000,
			ticks: []struct {
				price float64
				ts    int64
			}{
				{500, 310_000}, // bucket 300 000
				{510, 320_000}, // same bucket
				{520, 600_000}, // bucket 600 000 → rollover
			},
			wantOpenMs: 300_000,
			wantClose:  510,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			agg := New([]string{tt.interval})
			var lastClosed []domain.Candle
			for _, tc := range tt.ticks {
				closed := agg.Add(tick("BTCUSDT", tc.price, 1, tc.ts))
				if len(closed) > 0 {
					lastClosed = closed
				}
			}
			if lastClosed == nil {
				t.Fatal("expected at least one candle to close")
			}
			if lastClosed[0].OpenTimeMs != tt.wantOpenMs {
				t.Fatalf("open_time_ms: want %d, got %d", tt.wantOpenMs, lastClosed[0].OpenTimeMs)
			}
			if lastClosed[0].Close != tt.wantClose {
				t.Fatalf("close: want %v, got %v", tt.wantClose, lastClosed[0].Close)
			}
		})
	}
}

// ---------------------------------------------------------------------------
// Table-driven: OHLC correctness per interval
// ---------------------------------------------------------------------------

func TestOHLCPerIntervalTable(t *testing.T) {
	tests := []struct {
		name     string
		interval string
		ticks    []struct {
			price float64
			v     float64
			ts    int64
		}
		want domain.Candle
	}{
		{
			name:     "5m multiple ticks",
			interval: "5m",
			ticks: []struct {
				price float64
				v     float64
				ts    int64
			}{
				{10, 1, 0},
				{20, 2, 100_000},
				{5, 3, 200_000},
				{15, 4, 300_000}, // rollover — closed candle's Close is 5 (last tick before rollover)
			},
			want: domain.Candle{Symbol: "BTCUSDT", Interval: "5m", OpenTimeMs: 0, Open: 10, High: 20, Low: 5, Close: 5, Volume: 6, TradeCount: 3},
		},
		{
			name:     "1h descending prices",
			interval: "1h",
			ticks: []struct {
				price float64
				v     float64
				ts    int64
			}{
				{100, 1, 0},
				{90, 1, 1_000_000},
				{80, 1, 2_000_000},
				{70, 1, 3_600_000}, // rollover — closed candle's Close is 80
			},
			want: domain.Candle{Symbol: "BTCUSDT", Interval: "1h", OpenTimeMs: 0, Open: 100, High: 100, Low: 80, Close: 80, Volume: 3, TradeCount: 3},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			agg := New([]string{tt.interval})
			var closed []domain.Candle
			for _, tc := range tt.ticks {
				closed = append(closed, agg.Add(tick("BTCUSDT", tc.price, tc.v, tc.ts))...)
			}
			if len(closed) != 1 {
				t.Fatalf("expected exactly 1 closed candle, got %d", len(closed))
			}
			c := closed[0]
			if c.Open != tt.want.Open || c.High != tt.want.High || c.Low != tt.want.Low || c.Close != tt.want.Close {
				t.Fatalf("OHLC: want O=%v H=%v L=%v C=%v, got O=%v H=%v L=%v C=%v",
					tt.want.Open, tt.want.High, tt.want.Low, tt.want.Close,
					c.Open, c.High, c.Low, c.Close)
			}
			if c.Volume != tt.want.Volume {
				t.Fatalf("volume: want %v, got %v", tt.want.Volume, c.Volume)
			}
			if c.TradeCount != tt.want.TradeCount {
				t.Fatalf("trade_count: want %d, got %d", tt.want.TradeCount, c.TradeCount)
			}
		})
	}
}
