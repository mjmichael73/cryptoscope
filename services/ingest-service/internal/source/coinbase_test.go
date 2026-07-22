package source

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestCoinbaseName(t *testing.T) {
	c := NewCoinbase("https://api.exchange.coinbase.com")
	if c.Name() != "coinbase" {
		t.Fatalf("expected coinbase, got %s", c.Name())
	}
}

func TestCoinbaseFetchReturnsParsedTicks(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"price":"50000.00","volume":"100.5","time":"2026-01-15T10:30:00Z"}`))
	}))
	defer server.Close()

	c := NewCoinbase(server.URL)
	ticks, err := c.Fetch(context.Background(), []string{"BTCUSDT"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(ticks) != 1 {
		t.Fatalf("expected 1 tick, got %d", len(ticks))
	}
	if ticks[0].Symbol != "BTCUSDT" {
		t.Fatalf("expected BTCUSDT, got %s", ticks[0].Symbol)
	}
	if ticks[0].Price != 50000.00 {
		t.Fatalf("expected 50000.00, got %f", ticks[0].Price)
	}
	if ticks[0].Source != "coinbase" {
		t.Fatalf("expected coinbase source, got %s", ticks[0].Source)
	}
}

func TestCoinbaseFetchFiltersSymbols(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"price":"50000.00","volume":"100","time":"2026-01-15T10:30:00Z"}`))
	}))
	defer server.Close()

	c := NewCoinbase(server.URL)
	ticks, err := c.Fetch(context.Background(), []string{"BTCUSDT", "ETHUSDT"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(ticks) != 2 {
		t.Fatalf("expected 2 ticks, got %d", len(ticks))
	}
	if ticks[0].Symbol != "BTCUSDT" {
		t.Fatalf("expected BTCUSDT, got %s", ticks[0].Symbol)
	}
	if ticks[1].Symbol != "ETHUSDT" {
		t.Fatalf("expected ETHUSDT, got %s", ticks[1].Symbol)
	}
}

func TestCoinbaseFetchHandlesNonOKStatus(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusTooManyRequests)
	}))
	defer server.Close()

	c := NewCoinbase(server.URL)
	ticks, err := c.Fetch(context.Background(), []string{"BTCUSDT"})
	if err != nil {
		t.Fatalf("Fetch should not propagate per-symbol errors, got: %v", err)
	}
	if len(ticks) != 0 {
		t.Fatalf("expected 0 ticks for non-200 response, got %d", len(ticks))
	}
}

func TestCoinbaseFetchEmptyResponse(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{}`))
	}))
	defer server.Close()

	c := NewCoinbase(server.URL)
	ticks, err := c.Fetch(context.Background(), []string{"BTCUSDT"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(ticks) != 0 {
		t.Fatalf("expected 0 ticks for empty response, got %d", len(ticks))
	}
}

func TestToProduct(t *testing.T) {
	cases := []struct {
		input    string
		expected string
	}{
		{"BTCUSDT", "BTC-USD"},
		{"ETHUSDT", "ETH-USD"},
		{"SOLUSDT", "SOL-USD"},
		{"XRPUSDT", "XRP-USD"},
		{"DOGEUSDT", "DOGE-USD"},
		{"UNKNOWN", ""},
	}
	for _, tc := range cases {
		got := toProduct(tc.input)
		if got != tc.expected {
			t.Fatalf("toProduct(%s): expected %s, got %s", tc.input, tc.expected, got)
		}
	}
}
