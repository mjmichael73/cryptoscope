// Package domain holds the value types the stream processor works with.
package domain

// Tick mirrors the message produced by the ingest service. The processor only
// reads ticks, so this is a lean copy of the fields it needs.
type Tick struct {
	Symbol   string  `json:"symbol"`
	Price    float64 `json:"price"`
	Volume   float64 `json:"volume"`
	Source   string  `json:"source"`
	TsMillis int64   `json:"ts_millis"`
}

// Candle is an aggregated open, high, low, close bar for one symbol over one
// interval bucket. It is the unit stored in ClickHouse and served to clients.
type Candle struct {
	Symbol     string  `json:"symbol"`
	Interval   string  `json:"interval"`
	OpenTimeMs int64   `json:"open_time_ms"`
	Open       float64 `json:"open"`
	High       float64 `json:"high"`
	Low        float64 `json:"low"`
	Close      float64 `json:"close"`
	Volume     float64 `json:"volume"`
	TradeCount int64   `json:"trade_count"`
}
