package gateway

import (
	"context"
	"log/slog"
	"net/http"
	"sync"

	"github.com/mojimich2015/cryptoscope/libs/go/ratelimit"
)

// SSEConnectionLimiter enforces two limits on SSE connections:
//
//  1. MaxConcurrent: the maximum number of simultaneous open SSE connections
//     for a given key (tenant ID or remote address).
//  2. A per-key connection-rate limit backed by the Redis token bucket (Limiter),
//     which prevents connect/disconnect churn.
//
// When either limit is exceeded the handler returns 429.
type SSEConnectionLimiter struct {
	mu            sync.Mutex
	connections   map[string]int // key → count
	maxConcurrent int
	rateLimiter   *ratelimit.Limiter // optional, for connection-rate limiting
	logger        *slog.Logger
}

// NewSSEConnectionLimiter builds a limiter.  maxConcurrent caps simultaneous
// connections per key.  If rateLimiter is non-nil it is used to also enforce a
// per-key connection-rate limit (tokens-per-minute).  Set it to nil to skip
// connection-rate limiting.
func NewSSEConnectionLimiter(maxConcurrent int, rateLimiter *ratelimit.Limiter, logger *slog.Logger) *SSEConnectionLimiter {
	return &SSEConnectionLimiter{
		connections:   make(map[string]int),
		maxConcurrent: maxConcurrent,
		rateLimiter:   rateLimiter,
		logger:        logger,
	}
}

// acquire tries to register a new connection for key.  Returns true if allowed.
func (l *SSEConnectionLimiter) acquire(ctx context.Context, key string) bool {
	// 1. Check connection-rate limit first (Redis token bucket).
	if l.rateLimiter != nil {
		allowed, err := l.rateLimiter.Allow(ctx, "sse:"+key)
		if err != nil {
			l.logger.Error("SSE rate limit check failed", "error", err)
			// Fail open — don't block on Redis errors.
		} else if !allowed {
			return false
		}
	}

	// 2. Check concurrent-connection limit (in-process counter).
	l.mu.Lock()
	defer l.mu.Unlock()

	if l.connections[key] >= l.maxConcurrent {
		return false
	}
	l.connections[key]++
	return true
}

// release decrements the concurrent-connection counter for key.
func (l *SSEConnectionLimiter) release(key string) {
	l.mu.Lock()
	defer l.mu.Unlock()

	if l.connections[key] > 0 {
		l.connections[key]--
	}
}

// activeConnections returns the current count for a key (useful in tests).
func (l *SSEConnectionLimiter) activeConnections(key string) int {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.connections[key]
}

// Middleware returns an HTTP middleware that rate-limits SSE connections.
func (l *SSEConnectionLimiter) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		key := r.RemoteAddr
		if tid := r.Header.Get("X-Tenant-Id"); tid != "" {
			key = tid
		}

		if !l.acquire(r.Context(), key) {
			l.logger.Warn("SSE connection rate limited",
				"key", key,
				"active", l.activeConnections(key),
				"max", l.maxConcurrent,
			)
			w.Header().Set("Retry-After", "30")
			http.Error(w, `{"error":"SSE connection limit exceeded"}`, http.StatusTooManyRequests)
			return
		}

		// The SSE handler blocks until the client disconnects, so release
		// the slot when ServeHTTP returns.
		defer l.release(key)
		next.ServeHTTP(w, r)
	})
}
