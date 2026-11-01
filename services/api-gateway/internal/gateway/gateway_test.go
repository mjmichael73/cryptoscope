package gateway

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/go-chi/chi/v5"
	"github.com/mojimich2015/cryptoscope/services/api-gateway/internal/config"
)

func TestHealthz(t *testing.T) {
	gw := newTestGateway()
	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	w := httptest.NewRecorder()
	gw.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}

	var body map[string]string
	if err := json.NewDecoder(w.Body).Decode(&body); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	if body["status"] != "ok" {
		t.Fatalf("expected status ok, got %v", body)
	}
}

func TestRecoveryMiddleware(t *testing.T) {
	var buf strings.Builder
	logger := slog.New(slog.NewTextHandler(&buf, &slog.HandlerOptions{Level: slog.LevelDebug}))
	rw := &responseWriter{ResponseWriter: httptest.NewRecorder(), status: http.StatusOK}

	handler := RecoveryMiddleware(logger)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		panic("test panic")
	}))

	req := httptest.NewRequest(http.MethodGet, "/", nil)
	handler.ServeHTTP(rw, req)

	if rw.status != http.StatusInternalServerError {
		t.Fatalf("expected 500 after panic, got %d", rw.status)
	}
}

func TestTenantMiddlewareFillsDefault(t *testing.T) {
	var buf strings.Builder
	logger := slog.New(slog.NewTextHandler(&buf, &slog.HandlerOptions{Level: slog.LevelDebug}))
	handler := TenantMiddleware(logger, true)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest(http.MethodGet, "/", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	if !strings.Contains(buf.String(), "demo-tenant") {
		t.Fatalf("expected tenant resolution in logs, got: %s", buf.String())
	}
}

func TestTenantMiddlewarePassesExisting(t *testing.T) {
	var buf strings.Builder
	logger := slog.New(slog.NewTextHandler(&buf, &slog.HandlerOptions{Level: slog.LevelDebug}))
	handler := TenantMiddleware(logger, false)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set("X-Tenant-Id", "custom-tenant")
	req.Header.Set("X-Tenant-Slug", "custom")
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	if !strings.Contains(buf.String(), "custom-tenant") {
		t.Fatalf("expected custom tenant in logs, got: %s", buf.String())
	}
}

func TestTenantForwardingMiddlewareSetsHeaders(t *testing.T) {
	handler := TenantForwardingMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("X-Tenant-Id") != "test-id" {
			t.Fatalf("expected X-Tenant-Id header, got %s", r.Header.Get("X-Tenant-Id"))
		}
		if r.Header.Get("X-Tenant-Slug") != "test-slug" {
			t.Fatalf("expected X-Tenant-Slug header, got %s", r.Header.Get("X-Tenant-Slug"))
		}
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set("X-Tenant-Id", "test-id")
	req.Header.Set("X-Tenant-Slug", "test-slug")
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
}

func TestLoggingMiddleware(t *testing.T) {
	var buf strings.Builder
	logger := slog.New(slog.NewTextHandler(&buf, &slog.HandlerOptions{Level: slog.LevelInfo}))
	handler := LoggingMiddleware(logger)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	if !strings.Contains(buf.String(), "/test") {
		t.Fatalf("expected path in logs, got: %s", buf.String())
	}
}

func TestWriteJSON(t *testing.T) {
	w := httptest.NewRecorder()
	writeJSON(w, http.StatusCreated, map[string]string{"id": "abc"})

	if w.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d", w.Code)
	}
	ct := w.Header().Get("Content-Type")
	if !strings.Contains(ct, "application/json") {
		t.Fatalf("expected json content type, got %s", ct)
	}
	var body map[string]string
	if err := json.NewDecoder(w.Body).Decode(&body); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if body["id"] != "abc" {
		t.Fatalf("expected abc, got %s", body["id"])
	}
}

func TestWriteError(t *testing.T) {
	w := httptest.NewRecorder()
	writeError(w, http.StatusBadRequest, "bad input")

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
	var body map[string]string
	if err := json.NewDecoder(w.Body).Decode(&body); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if body["error"] != "bad input" {
		t.Fatalf("expected bad input, got %s", body["error"])
	}
}

func TestGetCandlesReturnsBadRequestWhenSymbolMissing(t *testing.T) {
	gw := newTestGateway()
	mux := chi.NewRouter()
	mux.Use(TenantMiddleware(gw.logger, false))
	mux.Get("/v1/candles", gw.getCandles)

	req := httptest.NewRequest(http.MethodGet, "/v1/candles", nil)
	req.Header.Set("X-Tenant-Id", "tenant-1")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
}

func TestGetCandlesDefaultsInterval(t *testing.T) {
	gw := newTestGateway()
	mux := chi.NewRouter()
	mux.Use(RecoveryMiddleware(gw.logger))
	mux.Use(TenantMiddleware(gw.logger, false))
	mux.Get("/v1/candles", gw.getCandles)

	req := httptest.NewRequest(http.MethodGet, "/v1/candles?symbol=BTCUSDT", nil)
	req.Header.Set("X-Tenant-Id", "tenant-1")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	// nil query client will cause 500, not 400 (means validation passed)
	if w.Code == http.StatusBadRequest {
		t.Fatal("expected validation to pass with symbol provided")
	}
}

func TestGetIndicatorReturnsBadRequestWhenSymbolMissing(t *testing.T) {
	gw := newTestGateway()
	mux := chi.NewRouter()
	mux.Use(TenantMiddleware(gw.logger, false))
	mux.Get("/v1/indicators", gw.getIndicator)

	req := httptest.NewRequest(http.MethodGet, "/v1/indicators", nil)
	req.Header.Set("X-Tenant-Id", "tenant-1")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
}

func TestGetIndicatorReturnsBadRequestWhenTypeMissing(t *testing.T) {
	gw := newTestGateway()
	mux := chi.NewRouter()
	mux.Use(TenantMiddleware(gw.logger, false))
	mux.Get("/v1/indicators", gw.getIndicator)

	req := httptest.NewRequest(http.MethodGet, "/v1/indicators?symbol=BTCUSDT", nil)
	req.Header.Set("X-Tenant-Id", "tenant-1")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
}

func TestListSymbolsReturns500WithNilClient(t *testing.T) {
	gw := newTestGateway()
	mux := chi.NewRouter()
	mux.Use(RecoveryMiddleware(gw.logger))
	mux.Use(TenantMiddleware(gw.logger, false))
	mux.Get("/v1/symbols", gw.listSymbols)

	req := httptest.NewRequest(http.MethodGet, "/v1/symbols", nil)
	req.Header.Set("X-Tenant-Id", "tenant-1")
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	// nil client -> 500 internal error
	if w.Code != http.StatusInternalServerError {
		t.Fatalf("expected 500 with nil client, got %d", w.Code)
	}
}

func TestNewRedisClient(t *testing.T) {
	client := NewRedisClient("localhost:6379", "", 0)
	if client == nil {
		t.Fatal("expected non-nil redis client")
	}
	defer client.Close()
}

func newSlog(buf *strings.Builder) *slog.Logger {
	return slog.New(slog.NewTextHandler(buf, &slog.HandlerOptions{Level: slog.LevelDebug}))
}

func newTestGateway() *Gateway {
	var buf strings.Builder
	logger := slog.New(slog.NewTextHandler(&buf, &slog.HandlerOptions{Level: slog.LevelDebug}))
	cfg := &config.Config{
		DevMode:     true,
		CommandHTTP: "http://localhost:18002",
		AlertHTTP:   "http://localhost:18003",
	}
	return New(nil, cfg, logger, nil, nil)
}
