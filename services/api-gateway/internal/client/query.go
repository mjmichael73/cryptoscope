package client

import (
	"context"
	"fmt"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/keepalive"

	cryptov1 "github.com/mojimich2015/cryptoscope/proto/cryptoscope/v1"
)

var intervalMap = map[string]cryptov1.Interval{
	"1m": cryptov1.Interval_INTERVAL_1M,
	"5m": cryptov1.Interval_INTERVAL_5M,
	"1h": cryptov1.Interval_INTERVAL_1H,
	"1d": cryptov1.Interval_INTERVAL_1D,
}

func intervalFromString(s string) cryptov1.Interval {
	if v, ok := intervalMap[s]; ok {
		return v
	}
	return cryptov1.Interval_INTERVAL_1M
}

type QueryClient struct {
	conn   *grpc.ClientConn
	client cryptov1.QueryServiceClient
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
		client: cryptov1.NewQueryServiceClient(conn),
	}, nil
}

func (c *QueryClient) GetCandles(ctx context.Context, tenantID, symbol, interval string, fromMs, toMs int64) ([]*cryptov1.Candle, error) {
	resp, err := c.client.GetCandles(ctx, &cryptov1.GetCandlesRequest{
		TenantId: tenantID,
		Symbol:   symbol,
		Interval: intervalFromString(interval),
		FromMs:   fromMs,
		ToMs:     toMs,
	})
	if err != nil {
		return nil, fmt.Errorf("get candles: %w", err)
	}
	return resp.Candles, nil
}

func (c *QueryClient) GetIndicator(ctx context.Context, tenantID, symbol, interval, indicatorType string, period int32) ([]*cryptov1.IndicatorPoint, error) {
	resp, err := c.client.GetIndicator(ctx, &cryptov1.GetIndicatorRequest{
		TenantId: tenantID,
		Symbol:   symbol,
		Interval: intervalFromString(interval),
		Type:     indicatorType,
		Period:   period,
	})
	if err != nil {
		return nil, fmt.Errorf("get indicator: %w", err)
	}
	return resp.Points, nil
}

func (c *QueryClient) ListSymbols(ctx context.Context, tenantID string) ([]string, error) {
	resp, err := c.client.ListSymbols(ctx, &cryptov1.ListSymbolsRequest{
		TenantId: tenantID,
	})
	if err != nil {
		return nil, fmt.Errorf("list symbols: %w", err)
	}
	return resp.Symbols, nil
}

func (c *QueryClient) SearchSymbols(ctx context.Context, tenantID, query string, limit int32) ([]*cryptov1.SymbolSummary, error) {
	resp, err := c.client.SearchSymbols(ctx, &cryptov1.SearchSymbolsRequest{
		TenantId: tenantID,
		Query:    query,
		Limit:    limit,
	})
	if err != nil {
		return nil, fmt.Errorf("search symbols: %w", err)
	}
	return resp.Symbols, nil
}

func (c *QueryClient) Close() error {
	return c.conn.Close()
}
