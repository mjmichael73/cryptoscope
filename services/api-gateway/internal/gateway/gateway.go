package gateway

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"

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

	public := chi.NewRouter()
	public.Get("/healthz", g.healthz)
	g.mux.Mount("/", public)

	protected := chi.NewRouter()
	protected.Use(auth.AuthMiddleware(keystore))
	protected.Use(RateLimitMiddleware(limiter, logger))

	protected.Get("/v1/candles", g.getCandles)
	protected.Get("/v1/indicators", g.getIndicator)
	protected.Get("/v1/symbols", g.listSymbols)

	protected.Post("/v1/watchlists", g.proxyToCommand)
	protected.Post("/v1/alert-rules", g.proxyToCommand)

	g.mux.Mount("/", protected)

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
	fromMs := parseInt64(r.URL.Query().Get("from_ms"), 0)
	toMs := parseInt64(r.URL.Query().Get("to_ms"), 0)

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
	period := parseInt(r.URL.Query().Get("period"), 14)
	fromMs := parseInt64(r.URL.Query().Get("from_ms"), 0)
	toMs := parseInt64(r.URL.Query().Get("to_ms"), 0)

	if symbol == "" {
		writeError(w, http.StatusBadRequest, "symbol is required")
		return
	}
	if indicatorType == "" {
		writeError(w, http.StatusBadRequest, "type is required")
		return
	}
	if interval == "" {
		interval = "1m"
	}

	points, err := g.query.GetIndicator(r.Context(), tenantID, symbol, interval, indicatorType, period, fromMs, toMs)
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

func parseInt64(s string, fallback int64) int64 {
	if s == "" {
		return fallback
	}
	var n int64
	if _, err := strings.NewReader(s).Read(&n); err == nil {
		return n
	}
	return fallback
}

func parseInt(s string, fallback int) int {
	if s == "" {
		return fallback
	}
	var n int
	if _, err := strings.NewReader(s).Read(&n); err == nil {
		return n
	}
	return fallback
}
