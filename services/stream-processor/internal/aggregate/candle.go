// Package aggregate builds candles from a stream of ticks.
//
// The aggregator keeps one open candle per symbol and interval in memory. When
// a tick arrives in a later bucket than the open candle, the open candle is
// finalized and emitted, and a fresh one starts. This keeps the hot path cheap
// and makes the logic easy to test without any infrastructure.
package aggregate

import (
	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/domain"
)

// IntervalMs maps a named interval to its width in milliseconds.
var IntervalMs = map[string]int64{
	"1m": 60_000,
	"5m": 300_000,
	"1h": 3_600_000,
	"1d": 86_400_000,
}

type key struct {
	symbol   string
	interval string
}

// Aggregator turns ticks into candles for a fixed set of intervals.
type Aggregator struct {
	intervals []string
	open      map[key]*domain.Candle
}

// New builds an Aggregator for the given intervals. Unknown intervals are
// ignored so a typo cannot silently produce wrong buckets.
func New(intervals []string) *Aggregator {
	valid := make([]string, 0, len(intervals))
	for _, in := range intervals {
		if _, ok := IntervalMs[in]; ok {
			valid = append(valid, in)
		}
	}
	return &Aggregator{intervals: valid, open: map[key]*domain.Candle{}}
}

// Add folds a tick into the open candles and returns any candles that the tick
// closed. A tick can close at most one candle per interval.
func (a *Aggregator) Add(tick domain.Tick) []domain.Candle {
	var closed []domain.Candle
	for _, interval := range a.intervals {
		width := IntervalMs[interval]
		bucket := tick.TsMillis - (tick.TsMillis % width)
		k := key{symbol: tick.Symbol, interval: interval}

		current, ok := a.open[k]
		if !ok {
			a.open[k] = newCandle(tick, interval, bucket)
			continue
		}

		if bucket > current.OpenTimeMs {
			closed = append(closed, *current)
			a.open[k] = newCandle(tick, interval, bucket)
			continue
		}

		applyTick(current, tick)
	}
	return closed
}

// Flush finalizes and returns every open candle. Call it on shutdown so no
// in-progress bar is lost.
func (a *Aggregator) Flush() []domain.Candle {
	out := make([]domain.Candle, 0, len(a.open))
	for k, candle := range a.open {
		out = append(out, *candle)
		delete(a.open, k)
	}
	return out
}

func newCandle(tick domain.Tick, interval string, bucket int64) *domain.Candle {
	return &domain.Candle{
		Symbol:     tick.Symbol,
		Interval:   interval,
		OpenTimeMs: bucket,
		Open:       tick.Price,
		High:       tick.Price,
		Low:        tick.Price,
		Close:      tick.Price,
		Volume:     tick.Volume,
		TradeCount: 1,
	}
}

func applyTick(candle *domain.Candle, tick domain.Tick) {
	if tick.Price > candle.High {
		candle.High = tick.Price
	}
	if tick.Price < candle.Low {
		candle.Low = tick.Price
	}
	candle.Close = tick.Price
	candle.Volume += tick.Volume
	candle.TradeCount++
}
