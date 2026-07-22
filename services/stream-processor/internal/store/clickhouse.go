package store

import (
	"context"
	"fmt"

	"github.com/ClickHouse/clickhouse-go/v2"
	"github.com/ClickHouse/clickhouse-go/v2/lib/driver"

	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/domain"
)

// ClickHouseCandles persists candles to ClickHouse.
//
// The target table uses a ReplacingMergeTree so a re-inserted candle for the
// same key replaces the old row on merge, which gives us idempotent writes.
type ClickHouseCandles struct {
	conn driver.Conn
}

// NewClickHouseCandles opens a connection to ClickHouse.
func NewClickHouseCandles(ctx context.Context, addr, database, user, password string) (*ClickHouseCandles, error) {
	conn, err := clickhouse.Open(&clickhouse.Options{
		Addr: []string{addr},
		Auth: clickhouse.Auth{
			Database: database,
			Username: user,
			Password: password,
		},
	})
	if err != nil {
		return nil, err
	}
	if err := conn.Ping(ctx); err != nil {
		return nil, fmt.Errorf("clickhouse ping: %w", err)
	}
	if err := ensureCandlesTable(ctx, conn); err != nil {
		return nil, fmt.Errorf("ensure candles table: %w", err)
	}
	return &ClickHouseCandles{conn: conn}, nil
}

func ensureCandlesTable(ctx context.Context, conn driver.Conn) error {
	return conn.Exec(ctx, `
		CREATE TABLE IF NOT EXISTS candles (
			tenant_id   String,
			symbol      String,
			interval    String,
			open_time   Int64,
			open        Float64,
			high        Float64,
			low         Float64,
			close       Float64,
			volume      Float64,
			trade_count Int32
		) ENGINE = ReplacingMergeTree()
		ORDER BY (tenant_id, symbol, interval, open_time)
	`)
}

// SaveCandles writes a batch of candles. The batch API keeps the write
// efficient even under a heavy tick load.
func (c *ClickHouseCandles) SaveCandles(ctx context.Context, tenantID string, candles []domain.Candle) error {
	batch, err := c.conn.PrepareBatch(ctx, `
		INSERT INTO candles (
			tenant_id, symbol, interval, open_time, open, high, low, close, volume, trade_count
		)`)
	if err != nil {
		return err
	}
	for _, candle := range candles {
		err = batch.Append(
			tenantID,
			candle.Symbol,
			candle.Interval,
			candle.OpenTimeMs,
			candle.Open,
			candle.High,
			candle.Low,
			candle.Close,
			candle.Volume,
			candle.TradeCount,
		)
		if err != nil {
			return err
		}
	}
	return batch.Send()
}
