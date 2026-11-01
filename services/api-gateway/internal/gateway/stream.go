package gateway

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"sync"
	"time"
)

// streamClient represents one SSE connection.
type streamClient struct {
	ch     chan []byte
	cancel chan struct{}
}

// StreamHub manages SSE connections and periodic candle polling.
type StreamHub struct {
	gateway *Gateway
	mu      sync.RWMutex
	clients map[*streamClient]struct{}
	logger  *slog.Logger
	stop    chan struct{}

	lastPoll time.Time
}

// NewStreamHub creates a hub that periodically fetches new candles and
// broadcasts them to connected SSE clients.
func NewStreamHub(g *Gateway, logger *slog.Logger) *StreamHub {
	h := &StreamHub{
		gateway:  g,
		clients:  make(map[*streamClient]struct{}),
		logger:   logger,
		stop:     make(chan struct{}),
		lastPoll: time.Now(),
	}
	go h.poll()
	return h
}

// Stop terminates the background polling goroutine.
func (h *StreamHub) Stop() {
	close(h.stop)
}

func (h *StreamHub) addClient(c *streamClient) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.clients[c] = struct{}{}
	h.logger.Debug("SSE client connected", "total", len(h.clients))
}

func (h *StreamHub) removeClient(c *streamClient) {
	h.mu.Lock()
	defer h.mu.Unlock()
	delete(h.clients, c)
	h.logger.Debug("SSE client disconnected", "total", len(h.clients))
}

func (h *StreamHub) broadcast(eventType string, data any) {
	payload, err := json.Marshal(map[string]any{"event": eventType, "data": data})
	if err != nil {
		h.logger.Warn("failed to marshal SSE payload", "error", err)
		return
	}

	h.mu.RLock()
	defer h.mu.RUnlock()
	for c := range h.clients {
		select {
		case c.ch <- payload:
		default:
			// Client too slow — drop the update.
		}
	}
}

// poll fetches new candles every 5 seconds and streams them.
func (h *StreamHub) poll() {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-h.stop:
			ticker.Stop()
			return
		case <-ticker.C:
			h.fetchUpdates()
		}
	}
}

func (h *StreamHub) fetchUpdates() {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	now := time.Now().UnixMilli()
	fromMs := h.lastPoll.UnixMilli()
	h.lastPoll = time.Now()

	intervals := []string{"1m", "5m", "1h"}
	for _, interval := range intervals {
		candles, err := h.gateway.query.GetCandles(ctx, "", "BTCUSDT", interval, fromMs, now)
		if err != nil {
			continue
		}
		for _, c := range candles {
			evt := map[string]any{
				"open_time_ms": c.OpenTime,
				"open":         c.Open,
				"high":         c.High,
				"low":          c.Low,
				"close":        c.Close,
				"volume":       c.Volume,
				"interval":     interval,
			}
			h.broadcast("candle", evt)
		}
	}
}

// handleSSE handles incoming SSE connection requests.
func (g *Gateway) handleSSE(w http.ResponseWriter, r *http.Request) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming not supported", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("X-Accel-Buffering", "no")

	client := &streamClient{
		ch:     make(chan []byte, 64),
		cancel: make(chan struct{}),
	}
	g.streamHub.addClient(client)
	defer g.streamHub.removeClient(client)

	// Send the initial connected event.
	fmt.Fprintf(w, "event: connected\ndata: {}\n\n")
	flusher.Flush()

	ctx := r.Context()
	for {
		select {
		case <-ctx.Done():
			return
		case <-client.cancel:
			return
		case msg := <-client.ch:
			fmt.Fprintf(w, "data: %s\n\n", msg)
			flusher.Flush()
		}
	}
}
