package source

import "testing"

func TestToProduct(t *testing.T) {
	cases := map[string]string{
		"BTCUSDT": "BTC-USD",
		"ETHUSDT": "ETH-USD",
		"SOLUSD":  "SOL-USD",
		"WEIRD":   "",
	}
	for symbol, want := range cases {
		if got := toProduct(symbol); got != want {
			t.Fatalf("toProduct(%q) = %q, want %q", symbol, got, want)
		}
	}
}
