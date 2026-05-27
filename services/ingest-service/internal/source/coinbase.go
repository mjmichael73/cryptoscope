package source

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/mojimich2015/cryptoscope/services/ingest-service/internal/domain"
)

// Coinbase reads prices from the public Coinbase Exchange API.
//
// Coinbase uses a product id like BTC-USD, so we translate our internal symbol
// format (BTCUSDT) into the product id it expects and back again.
type Coinbase struct {
	baseURL string
	client  *http.Client
}

// NewCoinbase builds a Coinbase source pointing at the given base URL.
func NewCoinbase(baseURL string) *Coinbase {
	return &Coinbase{
		baseURL: baseURL,
		client:  &http.Client{Timeout: 10 * time.Second},
	}
}

// Name returns the provider name.
func (c *Coinbase) Name() string { return "coinbase" }

type coinbaseTicker struct {
	Price  string `json:"price"`
	Volume string `json:"volume"`
}

// Fetch queries the ticker endpoint for each symbol one product at a time.
func (c *Coinbase) Fetch(ctx context.Context, symbols []string) ([]domain.Tick, error) {
	out := make([]domain.Tick, 0, len(symbols))
	for _, symbol := range symbols {
		product := toProduct(symbol)
		if product == "" {
			continue
		}
		tick, err := c.fetchOne(ctx, symbol, product)
		if err != nil {
			// A single failed product should not fail the whole batch.
			continue
		}
		out = append(out, tick)
	}
	return out, nil
}

func (c *Coinbase) fetchOne(ctx context.Context, symbol, product string) (domain.Tick, error) {
	endpoint := fmt.Sprintf("%s/products/%s/ticker", c.baseURL, product)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return domain.Tick{}, err
	}
	req.Header.Set("User-Agent", "cryptoscope-ingest")

	resp, err := c.client.Do(req)
	if err != nil {
		return domain.Tick{}, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return domain.Tick{}, fmt.Errorf("coinbase status %d for %s", resp.StatusCode, product)
	}

	var ticker coinbaseTicker
	if err := json.NewDecoder(resp.Body).Decode(&ticker); err != nil {
		return domain.Tick{}, err
	}
	price, err := parseFloat(ticker.Price)
	if err != nil {
		return domain.Tick{}, err
	}
	volume, _ := parseFloat(ticker.Volume)

	return domain.Tick{
		Symbol:   symbol,
		Price:    price,
		Volume:   volume,
		Source:   "coinbase",
		TsMillis: time.Now().UnixMilli(),
	}, nil
}

// toProduct converts an internal symbol like BTCUSDT into a Coinbase product id
// like BTC-USD. Coinbase quotes in USD rather than USDT, so we map the quote.
func toProduct(symbol string) string {
	switch {
	case strings.HasSuffix(symbol, "USDT"):
		base := strings.TrimSuffix(symbol, "USDT")
		return base + "-USD"
	case strings.HasSuffix(symbol, "USD"):
		base := strings.TrimSuffix(symbol, "USD")
		return base + "-USD"
	default:
		return ""
	}
}
