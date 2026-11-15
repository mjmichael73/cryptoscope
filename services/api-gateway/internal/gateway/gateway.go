package gateway

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strconv"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/mojimich2015/cryptoscope/libs/go/ratelimit"
	cryptov1 "github.com/mojimich2015/cryptoscope/proto/cryptoscope/v1"
	"github.com/mojimich2015/cryptoscope/services/api-gateway/internal/auth"
	"github.com/mojimich2015/cryptoscope/services/api-gateway/internal/client"
	"github.com/mojimich2015/cryptoscope/services/api-gateway/internal/config"
)

type Gateway struct {
	query      *client.QueryClient
	command    *httputil.ReverseProxy
	alert      *httputil.ReverseProxy
	logger     *slog.Logger
	mux        *chi.Mux
	streamHub  *StreamHub
	sseLimiter *SSEConnectionLimiter
}

func New(query *client.QueryClient, cfg *config.Config, logger *slog.Logger, limiter *ratelimit.Limiter, keystore *auth.CachingKeyStore) *Gateway {
	g := &Gateway{
		query:  query,
		logger: logger,
	}

	target, err := url.Parse(cfg.CommandHTTP)
	if err != nil {
		logger.Error("invalid command service URL", "error", err)
		g.command = &httputil.ReverseProxy{}
	} else {
		g.command = httputil.NewSingleHostReverseProxy(target)
	}

	alertTarget, err := url.Parse(cfg.AlertHTTP)
	if err != nil {
		logger.Error("invalid alert service URL", "error", err)
		g.alert = &httputil.ReverseProxy{}
	} else {
		g.alert = httputil.NewSingleHostReverseProxy(alertTarget)
	}

	g.mux = chi.NewRouter()

	g.mux.Use(RecoveryMiddleware(logger))
	g.mux.Use(LoggingMiddleware(logger))
	g.mux.Use(SecurityHeaders)
	if len(cfg.CORSAllowedOrigins) > 0 {
		g.mux.Use(CORSAllowedOrigins(cfg.CORSAllowedOrigins))
	}
	g.mux.Use(TenantMiddleware(logger, cfg.DevMode))
	g.mux.Use(TenantForwardingMiddleware)

	g.mux.Get("/healthz", g.healthz)
	g.mux.Get("/healthz/alert-service", g.proxyToAlertHealth)
	g.mux.Get("/healthz/command-service", g.proxyToCommandHealth)

	authMW := auth.AuthMiddleware(keystore)
	if cfg.DevMode {
		authMW = func(next http.Handler) http.Handler {
			return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				next.ServeHTTP(w, r)
			})
		}
		logger.Warn("running in dev mode, auth is DISABLED")
	}

	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Get("/v1/candles", g.getCandles)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Get("/v1/candles/export", g.exportCandles)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Get("/v1/indicators", g.getIndicator)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Get("/v1/symbols", g.listSymbols)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Get("/v1/symbols/search", g.searchSymbols)

	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Post("/v1/watchlists", g.proxyToCommand)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Get("/v1/watchlists", g.proxyToCommand)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Get("/v1/watchlists/*", g.proxyToCommand)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Put("/v1/watchlists/*", g.proxyToCommand)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Delete("/v1/watchlists/*", g.proxyToCommand)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Post("/v1/alert-rules", g.proxyToCommand)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Delete("/v1/alert-rules/*", g.proxyToCommand)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Get("/v1/alert-templates", g.proxyToCommand)

	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Get("/v1/alert-rules", g.proxyToAlert)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Get("/v1/alert-rules/*", g.proxyToAlert)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Get("/v1/triggers", g.proxyToAlert)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Delete("/v1/triggers", g.proxyToAlert)
	g.mux.With(authMW, RateLimitMiddleware(limiter, logger)).Post("/v1/triggers/{trigger_id}/ack", g.proxyToAlert)

	g.sseLimiter = NewSSEConnectionLimiter(5, limiter, logger)
	g.mux.With(authMW, g.sseLimiter.Middleware).Get("/v1/candles/stream", g.handleSSE)

	g.streamHub = NewStreamHub(g, logger)

	return g
}

func (g *Gateway) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	g.mux.ServeHTTP(w, r)
}

func (g *Gateway) healthz(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func (g *Gateway) getCandles(w http.ResponseWriter, r *http.Request) {
	tenantID := r.Header.Get("X-Tenant-Id")
	symbol := r.URL.Query().Get("symbol")
	interval := r.URL.Query().Get("interval")
	fromMs, _ := strconv.ParseInt(r.URL.Query().Get("from_ms"), 10, 64)
	toMs, _ := strconv.ParseInt(r.URL.Query().Get("to_ms"), 10, 64)

	if symbol == "" {
		writeError(w, http.StatusBadRequest, "symbol is required")
		return
	}

	if interval == "" {
		interval = "1m"
	}
	if fromMs == 0 {
		fromMs = time.Now().Add(-24 * time.Hour).UnixMilli()
	}
	if toMs == 0 {
		toMs = time.Now().UnixMilli()
	}

	candles, err := g.query.GetCandles(r.Context(), tenantID, symbol, interval, fromMs, toMs)
	if err != nil {
		g.logger.Error("get candles failed", "error", err)
		writeError(w, http.StatusInternalServerError, "query service error")
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{"candles": candleResponses(candles)})
}

func (g *Gateway) getIndicator(w http.ResponseWriter, r *http.Request) {
	tenantID := r.Header.Get("X-Tenant-Id")
	symbol := r.URL.Query().Get("symbol")
	indicatorType := r.URL.Query().Get("type")
	interval := r.URL.Query().Get("interval")
	period, _ := strconv.ParseInt(r.URL.Query().Get("period"), 10, 32)

	if symbol == "" {
		writeError(w, http.StatusBadRequest, "symbol is required")
		return
	}
	if indicatorType == "" {
		writeError(w, http.StatusBadRequest, "type is required (sma, ema, volatility)")
		return
	}
	if interval == "" {
		interval = "1m"
	}

	points, err := g.query.GetIndicator(r.Context(), tenantID, symbol, interval, indicatorType, int32(period))
	if err != nil {
		g.logger.Error("get indicator failed", "error", err)
		writeError(w, http.StatusInternalServerError, "query service error")
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{"points": indicatorResponses(points)})
}

func (g *Gateway) listSymbols(w http.ResponseWriter, r *http.Request) {
	tenantID := r.Header.Get("X-Tenant-Id")

	symbols, err := g.query.ListSymbols(r.Context(), tenantID)
	if err != nil {
		g.logger.Error("list symbols failed", "error", err)
		writeError(w, http.StatusInternalServerError, "query service error")
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{"symbols": nonil(symbols)})
}

func (g *Gateway) searchSymbols(w http.ResponseWriter, r *http.Request) {
	tenantID := r.Header.Get("X-Tenant-Id")
	q := r.URL.Query().Get("q")
	limitStr := r.URL.Query().Get("limit")

	limit := 50
	if limitStr != "" {
		parsed, err := strconv.Atoi(limitStr)
		if err != nil || parsed < 1 || parsed > 200 {
			writeError(w, http.StatusBadRequest, "limit must be between 1 and 200")
			return
		}
		limit = parsed
	}
	if len(q) > 100 {
		writeError(w, http.StatusBadRequest, "q must be at most 100 characters")
		return
	}

	summaries, err := g.query.SearchSymbols(r.Context(), tenantID, q, int32(limit))
	if err != nil {
		g.logger.Error("search symbols failed", "error", err)
		writeError(w, http.StatusInternalServerError, "query service error")
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{"symbols": nonil(summaries)})
}

func (g *Gateway) exportCandles(w http.ResponseWriter, r *http.Request) {
	tenantID := r.Header.Get("X-Tenant-Id")
	symbol := r.URL.Query().Get("symbol")
	interval := r.URL.Query().Get("interval")
	fromMs, _ := strconv.ParseInt(r.URL.Query().Get("from_ms"), 10, 64)
	toMs, _ := strconv.ParseInt(r.URL.Query().Get("to_ms"), 10, 64)
	format := r.URL.Query().Get("format")

	if symbol == "" {
		writeError(w, http.StatusBadRequest, "symbol is required")
		return
	}
	if interval == "" {
		interval = "1m"
	}
	if fromMs == 0 {
		fromMs = time.Now().Add(-24 * time.Hour).UnixMilli()
	}
	if toMs == 0 {
		toMs = time.Now().UnixMilli()
	}
	if format == "" {
		format = "csv"
	}

	candles, err := g.query.GetCandles(r.Context(), tenantID, symbol, interval, fromMs, toMs)
	if err != nil {
		g.logger.Error("export candles failed", "error", err)
		writeError(w, http.StatusInternalServerError, "query service error")
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{"candles": candleResponses(candles), "format": format})
}

func (g *Gateway) proxyToCommand(w http.ResponseWriter, r *http.Request) {
	g.command.ServeHTTP(w, r)
}

func (g *Gateway) proxyToAlert(w http.ResponseWriter, r *http.Request) {
	g.alert.ServeHTTP(w, r)
}

func (g *Gateway) proxyToCommandHealth(w http.ResponseWriter, r *http.Request) {
	r.URL.Path = "/healthz"
	g.command.ServeHTTP(w, r)
}

func (g *Gateway) proxyToAlertHealth(w http.ResponseWriter, r *http.Request) {
	r.URL.Path = "/healthz"
	g.alert.ServeHTTP(w, r)
}

func nonil[T any](s []T) []T {
	if s == nil {
		return []T{}
	}
	return s
}

type candleResponse struct {
	OpenTimeMs int64   `json:"open_time_ms"`
	Open       float64 `json:"open"`
	High       float64 `json:"high"`
	Low        float64 `json:"low"`
	Close      float64 `json:"close"`
	Volume     float64 `json:"volume"`
}

func candleResponses(candles []*cryptov1.Candle) []candleResponse {
	responses := make([]candleResponse, 0, len(candles))
	for _, candle := range candles {
		responses = append(responses, candleResponse{
			OpenTimeMs: candle.OpenTime,
			Open:       candle.Open,
			High:       candle.High,
			Low:        candle.Low,
			Close:      candle.Close,
			Volume:     candle.Volume,
		})
	}
	return responses
}

type indicatorResponse struct {
	TimeMs int64   `json:"time_ms"`
	Value  float64 `json:"value"`
}

func indicatorResponses(points []*cryptov1.IndicatorPoint) []indicatorResponse {
	responses := make([]indicatorResponse, 0, len(points))
	for _, point := range points {
		responses = append(responses, indicatorResponse{
			TimeMs: point.Time,
			Value:  point.Value,
		})
	}
	return responses
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
