package gateway

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
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

func TestHealthzReturnsJSON(t *testing.T) {
	gw := newTestGateway()
	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	w := httptest.NewRecorder()
	gw.ServeHTTP(w, req)

	ct := w.Header().Get("Content-Type")
	if !strings.Contains(ct, "application/json") {
		t.Fatalf("expected json content type, got %s", ct)
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
	handler := TenantMiddleware(logger)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
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
	handler := TenantMiddleware(logger)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
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

func newTestGateway() *Gateway {
	var buf strings.Builder
	logger := slog.New(slog.NewTextHandler(&buf, &slog.HandlerOptions{Level: slog.LevelDebug}))
	return New(nil, "http://localhost:18002", logger, nil, nil)
}
