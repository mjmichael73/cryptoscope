package gateway

import (
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"
)

func newTestSSELogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(&strings.Builder{}, &slog.HandlerOptions{Level: slog.LevelError}))
}

// ---------------------------------------------------------------------------
// Concurrent-connection limiter
// ---------------------------------------------------------------------------

func TestSSELimiterAllowsUpToMax(t *testing.T) {
	l := NewSSEConnectionLimiter(3, nil, newTestSSELogger())

	for i := 0; i < 3; i++ {
		if !l.acquire(t.Context(), "key-1") {
			t.Fatalf("connection %d should be allowed", i)
		}
	}
	if l.activeConnections("key-1") != 3 {
		t.Fatalf("expected 3 active, got %d", l.activeConnections("key-1"))
	}
}

func TestSSELimiterRejectsOverMax(t *testing.T) {
	l := NewSSEConnectionLimiter(2, nil, newTestSSELogger())

	l.acquire(t.Context(), "key-1")
	l.acquire(t.Context(), "key-1")

	if l.acquire(t.Context(), "key-1") {
		t.Fatal("should reject the 3rd connection on a key with max=2")
	}
}

func TestSSELimiterReleaseAllowsNewConnections(t *testing.T) {
	l := NewSSEConnectionLimiter(2, nil, newTestSSELogger())

	l.acquire(t.Context(), "key-1")
	l.acquire(t.Context(), "key-1")

	// Over limit.
	if l.acquire(t.Context(), "key-1") {
		t.Fatal("should be at limit")
	}

	// Release one slot.
	l.release("key-1")
	if l.activeConnections("key-1") != 1 {
		t.Fatalf("expected 1 active after release, got %d", l.activeConnections("key-1"))
	}

	// Now it should succeed.
	if !l.acquire(t.Context(), "key-1") {
		t.Fatal("should be allowed after release")
	}
}

func TestSSELimiterKeysAreIsolated(t *testing.T) {
	l := NewSSEConnectionLimiter(2, nil, newTestSSELogger())

	l.acquire(t.Context(), "tenant-A")
	l.acquire(t.Context(), "tenant-A")

	// tenant-A is full, but tenant-B should be unaffected.
	if !l.acquire(t.Context(), "tenant-B") {
		t.Fatal("different keys should have independent limits")
	}
}

func TestSSELimiterReleaseDoesNotGoNegative(t *testing.T) {
	l := NewSSEConnectionLimiter(5, nil, newTestSSELogger())

	l.release("nonexistent")
	if l.activeConnections("nonexistent") != 0 {
		t.Fatal("releasing nonexistent key should not create negative count")
	}
}

func TestSSELimiterConcurrentAccess(t *testing.T) {
	l := NewSSEConnectionLimiter(10, nil, newTestSSELogger())

	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			l.acquire(t.Context(), "concurrent-key")
			time.Sleep(5 * time.Millisecond)
			l.release("concurrent-key")
		}()
	}
	wg.Wait()

	if l.activeConnections("concurrent-key") != 0 {
		t.Fatalf("all connections released, expected 0, got %d", l.activeConnections("concurrent-key"))
	}
}

// ---------------------------------------------------------------------------
// Middleware
// ---------------------------------------------------------------------------

func TestSSEMiddlewareAllowsWithinLimit(t *testing.T) {
	l := NewSSEConnectionLimiter(2, nil, newTestSSELogger())
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	handler := l.Middleware(inner)

	req := httptest.NewRequest(http.MethodGet, "/v1/candles/stream", nil)
	req.RemoteAddr = "10.0.0.1:12345"
	rr := httptest.NewRecorder()

	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}
}

func TestSSEMiddlewareRejectsOverLimit(t *testing.T) {
	l := NewSSEConnectionLimiter(1, nil, newTestSSELogger())

	block := make(chan struct{})
	blocking := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		<-block // hold until test releases
	})
	handler := l.Middleware(blocking)

	// First connection — fills the slot (blocks in handler).
	req1 := httptest.NewRequest(http.MethodGet, "/v1/candles/stream", nil)
	req1.RemoteAddr = "10.0.0.1:12345"
	done := make(chan struct{})
	go func() {
		handler.ServeHTTP(httptest.NewRecorder(), req1)
		close(done)
	}()

	// Wait until the connection is registered.
	time.Sleep(20 * time.Millisecond)
	if l.activeConnections("10.0.0.1:12345") != 1 {
		t.Fatal("expected 1 active connection")
	}

	// Second connection — should be rejected.
	req2 := httptest.NewRequest(http.MethodGet, "/v1/candles/stream", nil)
	req2.RemoteAddr = "10.0.0.1:12345"
	rr2 := httptest.NewRecorder()
	handler.ServeHTTP(rr2, req2)
	if rr2.Code != http.StatusTooManyRequests {
		t.Fatalf("expected 429, got %d", rr2.Code)
	}
	if !strings.Contains(rr2.Body.String(), "limit exceeded") {
		t.Fatalf("expected limit-exceeded message, got: %s", rr2.Body.String())
	}

	// Release the blocked handler.
	close(block)
	<-done
}

func TestSSEMiddlewareReleasesAfterHandlerReturns(t *testing.T) {
	l := NewSSEConnectionLimiter(1, nil, newTestSSELogger())
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	handler := l.Middleware(inner)

	// Use slot.
	req1 := httptest.NewRequest(http.MethodGet, "/v1/candles/stream", nil)
	req1.RemoteAddr = "10.0.0.1:12345"
	handler.ServeHTTP(httptest.NewRecorder(), req1)

	// Slot should be released, so a new connection is allowed.
	req2 := httptest.NewRequest(http.MethodGet, "/v1/candles/stream", nil)
	req2.RemoteAddr = "10.0.0.1:12345"
	rr2 := httptest.NewRecorder()
	handler.ServeHTTP(rr2, req2)

	if rr2.Code != http.StatusOK {
		t.Fatalf("expected 200 after first handler returned, got %d", rr2.Code)
	}
}

func TestSSEMiddlewareUsesTenantIDAsKey(t *testing.T) {
	l := NewSSEConnectionLimiter(1, nil, newTestSSELogger())

	block := make(chan struct{})
	blocking := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		<-block
	})
	handler := l.Middleware(blocking)

	// Fill slot for tenant-1 (blocks).
	req1 := httptest.NewRequest(http.MethodGet, "/v1/candles/stream", nil)
	req1.RemoteAddr = "10.0.0.1:12345"
	req1.Header.Set("X-Tenant-Id", "tenant-1")
	done1 := make(chan struct{})
	go func() {
		handler.ServeHTTP(httptest.NewRecorder(), req1)
		close(done1)
	}()
	time.Sleep(20 * time.Millisecond)

	// tenant-2 on the same IP should succeed (different key) — but the
	// handler also blocks, so run it in a goroutine.
	rr2 := httptest.NewRecorder()
	req2 := httptest.NewRequest(http.MethodGet, "/v1/candles/stream", nil)
	req2.RemoteAddr = "10.0.0.1:12345"
	req2.Header.Set("X-Tenant-Id", "tenant-2")
	done2 := make(chan struct{})
	go func() {
		handler.ServeHTTP(rr2, req2)
		close(done2)
	}()
	time.Sleep(20 * time.Millisecond)

	if rr2.Code != http.StatusOK {
		t.Fatalf("different tenant should be allowed, got %d", rr2.Code)
	}

	// tenant-1 should be rejected (same key, already at limit).
	req3 := httptest.NewRequest(http.MethodGet, "/v1/candles/stream", nil)
	req3.RemoteAddr = "10.0.0.1:12345"
	req3.Header.Set("X-Tenant-Id", "tenant-1")
	rr3 := httptest.NewRecorder()
	handler.ServeHTTP(rr3, req3)

	if rr3.Code != http.StatusTooManyRequests {
		t.Fatalf("same tenant should be rejected, got %d", rr3.Code)
	}

	close(block)
	<-done1
	<-done2
}

func TestSSEMiddlewareReturnsRetryAfter(t *testing.T) {
	l := NewSSEConnectionLimiter(1, nil, newTestSSELogger())

	block := make(chan struct{})
	blocking := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		<-block
	})
	handler := l.Middleware(blocking)

	req1 := httptest.NewRequest(http.MethodGet, "/v1/candles/stream", nil)
	req1.RemoteAddr = "10.0.0.1:12345"
	done := make(chan struct{})
	go func() {
		handler.ServeHTTP(httptest.NewRecorder(), req1)
		close(done)
	}()
	time.Sleep(20 * time.Millisecond)

	req2 := httptest.NewRequest(http.MethodGet, "/v1/candles/stream", nil)
	req2.RemoteAddr = "10.0.0.1:12345"
	rr2 := httptest.NewRecorder()
	handler.ServeHTTP(rr2, req2)

	retryAfter := rr2.Header().Get("Retry-After")
	if retryAfter == "" {
		t.Fatal("expected Retry-After header on 429")
	}

	close(block)
	<-done
}

func TestSSEMiddlewareLargeMaxConnections(t *testing.T) {
	l := NewSSEConnectionLimiter(100, nil, newTestSSELogger())

	// Acquire all 100 slots via the limiter directly.
	for i := 0; i < 100; i++ {
		if !l.acquire(t.Context(), "big-key") {
			t.Fatalf("slot %d should be acquired", i)
		}
	}
	if l.activeConnections("big-key") != 100 {
		t.Fatalf("expected 100 active, got %d", l.activeConnections("big-key"))
	}

	// 101st should fail.
	if l.acquire(t.Context(), "big-key") {
		t.Fatal("101st acquire should fail")
	}

	// Release one, then acquire should succeed.
	l.release("big-key")
	if !l.acquire(t.Context(), "big-key") {
		t.Fatal("should succeed after release")
	}
}
