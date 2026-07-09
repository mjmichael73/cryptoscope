package gateway

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strconv"

	"github.com/go-chi/chi/v5"
	"github.com/mojimich2015/cryptoscope/libs/go/ratelimit"
	"github.com/mojimich2015/cryptoscope/services/api-gateway/internal/auth"
	"github.com/mojimich2015/cryptoscope/services/api-gateway/internal/client"
)

type Gateway struct {
	query   *client.QueryClient
	command *httputil.ReverseProxy
	logger  *slog.Logger
	mux     *chi.Mux
}

func New(query *client.QueryClient, commandURL string, logger *slog.Logger, limiter *ratelimit.Limiter, keystore *auth.CachingKeyStore) *Gateway {
	g := &Gateway{
		query:  query,
		logger: logger,
	}

	target, err := url.Parse(commandURL)
	if err != nil {
		logger.Error("invalid command service URL", "error", err)
		g.command = &httputil.ReverseProxy{}
	} else {
		g.command = httputil.NewSingleHostReverseProxy(target)
	}

	g.mux = chi.NewRouter()

	g.mux.Use(RecoveryMiddleware(logger))
	g.mux.Use(LoggingMiddleware(logger))
	g.mux.Use(TenantMiddleware(logger))
	g.mux.Use(TenantForwardingMiddleware)

	g.mux.Get("/healthz", g.healthz)

	g.mux.With(auth.AuthMiddleware(keystore), RateLimitMiddleware(limiter, logger)).Get("/v1/candles", g.getCandles)
	g.mux.With(auth.AuthMiddleware(keystore), RateLimitMiddleware(limiter, logger)).Get("/v1/indicators", g.getIndicator)
	g.mux.With(auth.AuthMiddleware(keystore), RateLimitMiddleware(limiter, logger)).Get("/v1/symbols", g.listSymbols)

	g.mux.With(auth.AuthMiddleware(keystore), RateLimitMiddleware(limiter, logger)).Post("/v1/watchlists", g.proxyToCommand)
	g.mux.With(auth.AuthMiddleware(keystore), RateLimitMiddleware(limiter, logger)).Post("/v1/alert-rules", g.proxyToCommand)

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

	candles, err := g.query.GetCandles(r.Context(), tenantID, symbol, interval, fromMs, toMs)
	if err != nil {
		g.logger.Error("get candles failed", "error", err)
		writeError(w, http.StatusInternalServerError, "query service error")
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{"candles": candles})
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

	writeJSON(w, http.StatusOK, map[string]any{"points": points})
}

func (g *Gateway) listSymbols(w http.ResponseWriter, r *http.Request) {
	tenantID := r.Header.Get("X-Tenant-Id")

	symbols, err := g.query.ListSymbols(r.Context(), tenantID)
	if err != nil {
		g.logger.Error("list symbols failed", "error", err)
		writeError(w, http.StatusInternalServerError, "query service error")
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{"symbols": symbols})
}

func (g *Gateway) proxyToCommand(w http.ResponseWriter, r *http.Request) {
	g.command.ServeHTTP(w, r)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
