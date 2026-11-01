package gateway

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestStreamHubBroadcastReachesAllClients(t *testing.T) {
	hub := newTestStreamHub()

	c1 := &streamClient{ch: make(chan []byte, 16), cancel: make(chan struct{})}
	c2 := &streamClient{ch: make(chan []byte, 16), cancel: make(chan struct{})}
	hub.addClient(c1)
	hub.addClient(c2)

	hub.broadcast("candle", map[string]any{"close": 100.0})

	select {
	case msg := <-c1.ch:
		assertContainsEvent(t, msg, "candle")
	case <-time.After(time.Second):
		t.Fatal("c1 did not receive broadcast")
	}

	select {
	case msg := <-c2.ch:
		assertContainsEvent(t, msg, "candle")
	case <-time.After(time.Second):
		t.Fatal("c2 did not receive broadcast")
	}

	hub.Stop()
}

func TestStreamHubBroadcastDropsForSlowClients(t *testing.T) {
	hub := newTestStreamHub()

	// Client with a full unbuffered channel.
	c := &streamClient{ch: make(chan []byte, 1), cancel: make(chan struct{})}
	hub.addClient(c)

	// Fill the buffer.
	hub.broadcast("candle", map[string]any{"close": 1.0})
	// This should not block (drop).
	hub.broadcast("candle", map[string]any{"close": 2.0})

	select {
	case <-c.ch:
		// first message received
	default:
		t.Fatal("expected first message in buffer")
	}

	hub.Stop()
}

func TestStreamHubRemoveClient(t *testing.T) {
	hub := newTestStreamHub()

	c := &streamClient{ch: make(chan []byte, 16), cancel: make(chan struct{})}
	hub.addClient(c)
	hub.removeClient(c)

	hub.broadcast("candle", map[string]any{"close": 1.0})

	select {
	case <-c.ch:
		t.Fatal("removed client should not receive broadcast")
	case <-time.After(100 * time.Millisecond):
		// expected
	}

	hub.Stop()
}

func TestStreamHubRemoveNonexistentClient(t *testing.T) {
	hub := newTestStreamHub()

	c := &streamClient{ch: make(chan []byte, 1), cancel: make(chan struct{})}
	// Should not panic.
	hub.removeClient(c)

	hub.Stop()
}

func TestStreamHubConcurrentBroadcast(t *testing.T) {
	hub := newTestStreamHub()

	clients := make([]*streamClient, 10)
	for i := range clients {
		clients[i] = &streamClient{ch: make(chan []byte, 64), cancel: make(chan struct{})}
		hub.addClient(clients[i])
	}

	// Broadcast from multiple goroutines.
	for i := 0; i < 20; i++ {
		go hub.broadcast("candle", map[string]any{"i": i})
	}

	time.Sleep(100 * time.Millisecond)
	hub.Stop()
}

func TestHandleSSETSHeaders(t *testing.T) {
	hub := newTestStreamHub()
	gw := &Gateway{streamHub: hub, logger: hub.logger}

	req := httptest.NewRequest(http.MethodGet, "/v1/candles/stream", nil)
	rr := httptest.NewRecorder()

	ctx, cancel := context.WithCancel(req.Context())
	req = req.WithContext(ctx)

	done := make(chan struct{})
	go func() {
		defer close(done)
		gw.handleSSE(rr, req)
	}()

	// Wait for the initial connected event.
	time.Sleep(50 * time.Millisecond)
	cancel()
	<-done

	body := rr.Body.String()
	if !strings.Contains(body, "event: connected") {
		t.Fatalf("expected 'event: connected' in response, got: %s", body)
	}

	ct := rr.Header().Get("Content-Type")
	if ct != "text/event-stream" {
		t.Fatalf("expected text/event-stream, got %s", ct)
	}

	cache := rr.Header().Get("Cache-Control")
	if cache != "no-cache" {
		t.Fatalf("expected no-cache, got %s", cache)
	}

	hub.Stop()
}

func TestHandleSSEStreamsBroadcastData(t *testing.T) {
	hub := newTestStreamHub()
	gw := &Gateway{streamHub: hub, logger: hub.logger}

	req := httptest.NewRequest(http.MethodGet, "/v1/candles/stream", nil)
	rr := httptest.NewRecorder()

	ctx, cancel := context.WithCancel(req.Context())
	req = req.WithContext(ctx)

	done := make(chan struct{})
	go func() {
		defer close(done)
		gw.handleSSE(rr, req)
	}()

	// Wait for client to be registered.
	time.Sleep(50 * time.Millisecond)

	// Broadcast a candle event.
	hub.broadcast("candle", map[string]any{"close": 9999.0})

	time.Sleep(100 * time.Millisecond)
	cancel()
	<-done

	body := rr.Body.String()
	if !strings.Contains(body, "event: connected") {
		t.Fatal("missing connected event")
	}
	if !strings.Contains(body, "9999") {
		t.Fatalf("expected candle data in response, got: %s", body)
	}

	hub.Stop()
}

func TestHandleSSENoFlusherReturns500(t *testing.T) {
	hub := newTestStreamHub()
	gw := &Gateway{streamHub: hub, logger: hub.logger}

	req := httptest.NewRequest(http.MethodGet, "/v1/candles/stream", nil)

	// Use a ResponseWriter that does NOT implement Flusher.
	w := &nonFlusherWriter{ResponseWriter: httptest.NewRecorder()}
	gw.handleSSE(w, req)

	if w.status != http.StatusInternalServerError {
		t.Fatalf("expected 500, got %d", w.status)
	}

	hub.Stop()
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func newTestStreamHub() *StreamHub {
	logger := slog.New(slog.NewTextHandler(&strings.Builder{}, &slog.HandlerOptions{Level: slog.LevelError}))
	gw := &Gateway{logger: logger}
	hub := &StreamHub{
		gateway:  gw,
		clients:  make(map[*streamClient]struct{}),
		logger:   logger,
		stop:     make(chan struct{}),
		lastPoll: time.Now(),
	}
	return hub
}

func assertContainsEvent(t *testing.T, msg []byte, eventType string) {
	t.Helper()
	var envelope map[string]any
	if err := json.Unmarshal(msg, &envelope); err != nil {
		t.Fatalf("failed to unmarshal SSE message: %v", err)
	}
	if envelope["event"] != eventType {
		t.Fatalf("expected event type %q, got %v", eventType, envelope["event"])
	}
}

// nonFlusherWriter wraps an http.ResponseWriter but does not implement http.Flusher.
type nonFlusherWriter struct {
	http.ResponseWriter
	status int
}

func (w *nonFlusherWriter) WriteHeader(code int) {
	w.status = code
	w.ResponseWriter.WriteHeader(code)
}
