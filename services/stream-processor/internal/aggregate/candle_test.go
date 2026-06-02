package aggregate

import (
	"testing"

	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/domain"
)

func tick(symbol string, price, volume float64, ts int64) domain.Tick {
	return domain.Tick{Symbol: symbol, Price: price, Volume: volume, TsMillis: ts}
}

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

func TestNewIgnoresUnknownIntervals(t *testing.T) {
	agg := New([]string{"1m", "bogus"})
	agg.Add(tick("BTCUSDT", 100, 1, 0))
	if got := agg.Flush(); len(got) != 1 {
		t.Fatalf("unknown interval should be dropped, got %d candles", len(got))
	}
}
