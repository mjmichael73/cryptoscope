package domain

import (
	"encoding/json"
	"testing"
)

// ---------------------------------------------------------------------------
// Tick
// ---------------------------------------------------------------------------

func TestTickJSONRoundTrip(t *testing.T) {
	original := Tick{
		Symbol:   "BTCUSDT",
		Price:    42_500.75,
		Volume:   0.123,
		Source:   "binance",
		TsMillis: 1_700_000_000_000,
	}

	b, err := json.Marshal(original)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	var decoded Tick
	if err := json.Unmarshal(b, &decoded); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}

	if decoded != original {
		t.Fatalf("round-trip mismatch:\n  original: %+v\n  decoded:  %+v", original, decoded)
	}
}

func TestTickJSONFieldNames(t *testing.T) {
	tick := Tick{Symbol: "ETHUSDT", Price: 2000, Volume: 5, Source: "coinbase", TsMillis: 1000}
	b, err := json.Marshal(tick)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	var raw map[string]json.RawMessage
	if err := json.Unmarshal(b, &raw); err != nil {
		t.Fatalf("unmarshal raw: %v", err)
	}

	expectedKeys := []string{"symbol", "price", "volume", "source", "ts_millis"}
	for _, key := range expectedKeys {
		if _, ok := raw[key]; !ok {
			t.Fatalf("expected JSON key %q", key)
		}
	}
}

func TestTickJSONFromExternalPayload(t *testing.T) {
	payload := `{"symbol":"SOLUSDT","price":98.5,"volume":12.3,"source":"binance","ts_millis":1700000000000}`
	var tick Tick
	if err := json.Unmarshal([]byte(payload), &tick); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if tick.Symbol != "SOLUSDT" {
		t.Fatalf("symbol: want SOLUSDT, got %s", tick.Symbol)
	}
	if tick.Price != 98.5 {
		t.Fatalf("price: want 98.5, got %v", tick.Price)
	}
	if tick.Volume != 12.3 {
		t.Fatalf("volume: want 12.3, got %v", tick.Volume)
	}
}

// ---------------------------------------------------------------------------
// Candle
// ---------------------------------------------------------------------------

func TestCandleJSONRoundTrip(t *testing.T) {
	original := Candle{
		Symbol:     "BTCUSDT",
		Interval:   "1m",
		OpenTimeMs: 1_700_000_000_000,
		Open:       42_000,
		High:       42_500,
		Low:        41_800,
		Close:      42_300,
		Volume:     123.456,
		TradeCount: 789,
	}

	b, err := json.Marshal(original)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	var decoded Candle
	if err := json.Unmarshal(b, &decoded); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}

	if decoded != original {
		t.Fatalf("round-trip mismatch:\n  original: %+v\n  decoded:  %+v", original, decoded)
	}
}

func TestCandleJSONFieldNames(t *testing.T) {
	candle := Candle{Symbol: "ETH", Interval: "1h", OpenTimeMs: 1000, Open: 1, High: 2, Low: 0, Close: 1.5, Volume: 10, TradeCount: 5}
	b, err := json.Marshal(candle)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	var raw map[string]json.RawMessage
	if err := json.Unmarshal(b, &raw); err != nil {
		t.Fatalf("unmarshal raw: %v", err)
	}

	expectedKeys := []string{"symbol", "interval", "open_time_ms", "open", "high", "low", "close", "volume", "trade_count"}
	for _, key := range expectedKeys {
		if _, ok := raw[key]; !ok {
			t.Fatalf("expected JSON key %q", key)
		}
	}
}

func TestCandleJSONZeroValues(t *testing.T) {
	candle := Candle{}
	b, err := json.Marshal(candle)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	var decoded Candle
	if err := json.Unmarshal(b, &decoded); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}

	if decoded != (Candle{}) {
		t.Fatalf("expected zero-value candle, got %+v", decoded)
	}
}

// ---------------------------------------------------------------------------
// CandleUpdatedEvent
// ---------------------------------------------------------------------------

func TestCandleUpdatedEventJSONRoundTrip(t *testing.T) {
	original := CandleUpdatedEvent{
		EventType:   "candle_updated",
		AggregateID: "BTCUSDT:1m:1700000000000",
		TenantID:    "00000000-0000-0000-0000-000000000001",
		Data: Candle{
			Symbol:     "BTCUSDT",
			Interval:   "1m",
			OpenTimeMs: 1_700_000_000_000,
			Open:       42_000,
			High:       42_500,
			Low:        41_800,
			Close:      42_300,
			Volume:     100,
			TradeCount: 50,
		},
		Timestamp: 1_700_000_060_000,
	}

	b, err := json.Marshal(original)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	var decoded CandleUpdatedEvent
	if err := json.Unmarshal(b, &decoded); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}

	if decoded != original {
		t.Fatalf("round-trip mismatch:\n  original: %+v\n  decoded:  %+v", original, decoded)
	}
}

func TestCandleUpdatedEventJSONFieldNames(t *testing.T) {
	event := CandleUpdatedEvent{
		EventType:   "candle_updated",
		AggregateID: "BTCUSDT:1m:0",
		TenantID:    "tenant-1",
		Data:        Candle{Symbol: "BTC"},
		Timestamp:   1000,
	}
	b, err := json.Marshal(event)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	var raw map[string]json.RawMessage
	if err := json.Unmarshal(b, &raw); err != nil {
		t.Fatalf("unmarshal raw: %v", err)
	}

	expectedKeys := []string{"event_type", "aggregate_id", "tenant_id", "data", "timestamp"}
	for _, key := range expectedKeys {
		if _, ok := raw[key]; !ok {
			t.Fatalf("expected JSON key %q", key)
		}
	}
}

func TestCandleUpdatedEventJSONNestedData(t *testing.T) {
	event := CandleUpdatedEvent{
		EventType: "candle_updated",
		Data: Candle{
			Symbol:     "ETHUSDT",
			Interval:   "5m",
			OpenTimeMs: 300_000,
			Open:       2000,
			High:       2100,
			Low:        1900,
			Close:      2050,
			Volume:     500,
			TradeCount: 120,
		},
	}

	b, err := json.Marshal(event)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	var raw map[string]json.RawMessage
	if err := json.Unmarshal(b, &raw); err != nil {
		t.Fatalf("unmarshal raw: %v", err)
	}

	// Verify nested data is a JSON object, not flattened.
	dataRaw, ok := raw["data"]
	if !ok {
		t.Fatal("expected \"data\" key")
	}
	var dataObj map[string]json.RawMessage
	if err := json.Unmarshal(dataRaw, &dataObj); err != nil {
		t.Fatalf("data is not an object: %v", err)
	}
	if _, ok := dataObj["symbol"]; !ok {
		t.Fatal("expected \"symbol\" in nested data")
	}
	if _, ok := dataObj["trade_count"]; !ok {
		t.Fatal("expected \"trade_count\" in nested data")
	}
}

// ---------------------------------------------------------------------------
// JSON compatibility with ingest-service tick format
// ---------------------------------------------------------------------------

func TestTickJSONCompatibleWithIngestFormat(t *testing.T) {
	// This is the format the ingest-service produces.
	payload := `{"symbol":"BTCUSDT","price":67890.5,"volume":0.042,"source":"binance","ts_millis":1720000000000}`
	var tick Tick
	if err := json.Unmarshal([]byte(payload), &tick); err != nil {
		t.Fatalf("unmarshal ingest payload: %v", err)
	}

	if tick.Symbol != "BTCUSDT" {
		t.Fatalf("symbol: want BTCUSDT, got %s", tick.Symbol)
	}
	if tick.Price != 67890.5 {
		t.Fatalf("price: want 67890.5, got %v", tick.Price)
	}
	if tick.Volume != 0.042 {
		t.Fatalf("volume: want 0.042, got %v", tick.Volume)
	}
	if tick.Source != "binance" {
		t.Fatalf("source: want binance, got %s", tick.Source)
	}
	if tick.TsMillis != 1720000000000 {
		t.Fatalf("ts_millis: want 1720000000000, got %d", tick.TsMillis)
	}
}
