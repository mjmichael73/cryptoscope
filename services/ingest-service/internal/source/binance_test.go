package source

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestBinanceFetchFiltersToWantedSymbols(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`[
			{"symbol":"BTCUSDT","price":"51000.10"},
			{"symbol":"ETHUSDT","price":"2400.55"},
			{"symbol":"DOGEUSDT","price":"0.12"}
		]`))
	}))
	defer server.Close()

	src := NewBinance(server.URL)
	ticks, err := src.Fetch(context.Background(), []string{"BTCUSDT", "ETHUSDT"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(ticks) != 2 {
		t.Fatalf("expected 2 ticks, got %d", len(ticks))
	}
	for _, tick := range ticks {
		if tick.Source != "binance" {
			t.Fatalf("expected source binance, got %q", tick.Source)
		}
		if tick.Price <= 0 {
			t.Fatalf("expected positive price, got %v", tick.Price)
		}
	}
}

func TestBinanceFetchHandlesNonOKStatus(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusTooManyRequests)
	}))
	defer server.Close()

	src := NewBinance(server.URL)
	if _, err := src.Fetch(context.Background(), []string{"BTCUSDT"}); err == nil {
		t.Fatal("expected an error on non-OK status")
	}
}
