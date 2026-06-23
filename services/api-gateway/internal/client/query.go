package client

import (
	"context"
	"fmt"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/keepalive"

	"github.com/mojimich2015/cryptoscope/proto/cryptoscope/v1"
)

type QueryClient struct {
	conn   *grpc.ClientConn
	client cryptoscope.QueryServiceClient
}

func NewQueryClient(addr string) (*QueryClient, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	conn, err := grpc.DialContext(ctx, addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithKeepaliveParams(keepalive.ClientParameters{
			Time:    30 * time.Second,
			Timeout: 10 * time.Second,
		}),
	)
	if err != nil {
		return nil, fmt.Errorf("grpc dial: %w", err)
	}

	return &QueryClient{
		conn:   conn,
		client: cryptoscope.NewQueryServiceClient(conn),
	}, nil
}

func (c *QueryClient) GetCandles(ctx context.Context, tenantID, symbol, interval string, fromMs, toMs int64) ([]*cryptoscope.Candle, error) {
	resp, err := c.client.GetCandles(ctx, &cryptoscope.GetCandlesRequest{
		TenantId: tenantID,
		Symbol:   symbol,
		Interval: cryptoscope.Interval(cryptoscope.Interval_value[interval]),
		FromMs:   fromMs,
		ToMs:     toMs,
	})
	if err != nil {
		return nil, fmt.Errorf("get candles: %w", err)
	}
	return resp.Candles, nil
}

func (c *QueryClient) GetIndicator(ctx context.Context, tenantID, symbol, interval, indicatorType string, period int, fromMs, toMs int64) ([]*cryptoscope.IndicatorPoint, error) {
	resp, err := c.client.GetIndicator(ctx, &cryptoscope.GetIndicatorRequest{
		TenantId: tenantID,
		Symbol:   symbol,
		Interval: cryptoscope.Interval(cryptoscope.Interval_value[interval]),
		Type:     indicatorType,
		Period:   int32(period),
		FromMs:   fromMs,
		ToMs:     toMs,
	})
	if err != nil {
		return nil, fmt.Errorf("get indicator: %w", err)
	}
	return resp.Points, nil
}

func (c *QueryClient) ListSymbols(ctx context.Context, tenantID string) ([]string, error) {
	resp, err := c.client.ListSymbols(ctx, &cryptoscope.ListSymbolsRequest{
		TenantId: tenantID,
	})
	if err != nil {
		return nil, fmt.Errorf("list symbols: %w", err)
	}
	return resp.Symbols, nil
}

func (c *QueryClient) Close() error {
	return c.conn.Close()
}
