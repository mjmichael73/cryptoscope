// Package source contains the public market data clients.
//
// Each source knows how to reach one public API and map its response into the
// common domain.Tick. The APIs used here need no key and no authentication.
package source

import (
	"context"

	"github.com/mojimich2015/cryptoscope/services/ingest-service/internal/domain"
)

// Source fetches the latest ticks for a set of symbols from one provider.
type Source interface {
	// Name identifies the provider, for example "binance".
	Name() string
	// Fetch returns the latest tick for each requested symbol. A source may
	// return fewer ticks than requested when a symbol is not listed.
	Fetch(ctx context.Context, symbols []string) ([]domain.Tick, error)
}
