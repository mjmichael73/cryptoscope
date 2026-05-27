package domain

import "testing"

func TestDedupeKeyStableWithinSameSecond(t *testing.T) {
	a := Tick{Symbol: "BTCUSDT", Price: 1, Source: "binance", TsMillis: 1_700_000_000_123}
	b := Tick{Symbol: "BTCUSDT", Price: 2, Source: "binance", TsMillis: 1_700_000_000_876}
	if a.DedupeKey() != b.DedupeKey() {
		t.Fatal("ticks in the same second from the same source should share a key")
	}
}

func TestDedupeKeyDiffersAcrossSeconds(t *testing.T) {
	a := Tick{Symbol: "BTCUSDT", Source: "binance", TsMillis: 1_700_000_000_000}
	b := Tick{Symbol: "BTCUSDT", Source: "binance", TsMillis: 1_700_000_001_000}
	if a.DedupeKey() == b.DedupeKey() {
		t.Fatal("ticks in different seconds should have different keys")
	}
}

func TestDedupeKeyDiffersAcrossSources(t *testing.T) {
	a := Tick{Symbol: "BTCUSDT", Source: "binance", TsMillis: 1_700_000_000_000}
	b := Tick{Symbol: "BTCUSDT", Source: "coinbase", TsMillis: 1_700_000_000_000}
	if a.DedupeKey() == b.DedupeKey() {
		t.Fatal("ticks from different sources should have different keys")
	}
}

func TestValid(t *testing.T) {
	cases := []struct {
		name string
		tick Tick
		want bool
	}{
		{"complete", Tick{Symbol: "BTCUSDT", Price: 1, Source: "binance", TsMillis: 1}, true},
		{"no symbol", Tick{Price: 1, Source: "binance", TsMillis: 1}, false},
		{"no source", Tick{Symbol: "BTCUSDT", Price: 1, TsMillis: 1}, false},
		{"zero price", Tick{Symbol: "BTCUSDT", Source: "binance", TsMillis: 1}, false},
		{"no timestamp", Tick{Symbol: "BTCUSDT", Price: 1, Source: "binance"}, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := tc.tick.Valid(); got != tc.want {
				t.Fatalf("Valid() = %v, want %v", got, tc.want)
			}
		})
	}
}
