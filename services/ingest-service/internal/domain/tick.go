// Package domain holds the value types the ingest service works with.
package domain

import (
	"crypto/sha1"
	"encoding/hex"
	"fmt"
)

// Tick is a single normalized price observation from a market data source.
// Every source is mapped into this shape so the rest of the pipeline does not
// care where a price came from.
type Tick struct {
	Symbol   string  `json:"symbol"`
	Price    float64 `json:"price"`
	Volume   float64 `json:"volume"`
	Source   string  `json:"source"`
	TsMillis int64   `json:"ts_millis"`
}

// DedupeKey returns a deterministic key for the tick. The same observation from
// the same source at the same second collapses to one key, which is what lets
// the pipeline drop duplicates after a retry.
func (t Tick) DedupeKey() string {
	seconds := t.TsMillis / 1000
	raw := fmt.Sprintf("%s|%s|%d", t.Source, t.Symbol, seconds)
	sum := sha1.Sum([]byte(raw))
	return hex.EncodeToString(sum[:])
}

// Valid reports whether the tick carries the minimum fields the pipeline needs.
func (t Tick) Valid() bool {
	return t.Symbol != "" && t.Source != "" && t.Price > 0 && t.TsMillis > 0
}
