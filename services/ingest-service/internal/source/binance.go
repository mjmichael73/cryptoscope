package source

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/mojimich2015/cryptoscope/services/ingest-service/internal/domain"
)

// Binance reads spot prices from the public Binance REST API.
type Binance struct {
	baseURL string
	client  *http.Client
}

// NewBinance builds a Binance source pointing at the given base URL.
func NewBinance(baseURL string) *Binance {
	return &Binance{
		baseURL: baseURL,
		client:  &http.Client{Timeout: 10 * time.Second},
	}
}

// Name returns the provider name.
func (b *Binance) Name() string { return "binance" }

type binanceTicker struct {
	Symbol string `json:"symbol"`
	Price  string `json:"price"`
}

// Fetch pulls the current price for each symbol. Binance uses symbols like
// BTCUSDT with no separator, which matches our internal symbol format.
func (b *Binance) Fetch(ctx context.Context, symbols []string) ([]domain.Tick, error) {
	endpoint := b.baseURL + "/api/v3/ticker/price"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, err
	}

	resp, err := b.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("binance fetch: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("binance returned status %d", resp.StatusCode)
	}

	var tickers []binanceTicker
	if err := json.NewDecoder(resp.Body).Decode(&tickers); err != nil {
		return nil, fmt.Errorf("binance decode: %w", err)
	}

	wanted := make(map[string]struct{}, len(symbols))
	for _, s := range symbols {
		wanted[s] = struct{}{}
	}

	now := time.Now().UnixMilli()
	out := make([]domain.Tick, 0, len(symbols))
	for _, t := range tickers {
		if _, ok := wanted[t.Symbol]; !ok {
			continue
		}
		price, perr := parseFloat(t.Price)
		if perr != nil {
			continue
		}
		out = append(out, domain.Tick{
			Symbol:   t.Symbol,
			Price:    price,
			Source:   b.Name(),
			TsMillis: now,
		})
	}
	return out, nil
}
