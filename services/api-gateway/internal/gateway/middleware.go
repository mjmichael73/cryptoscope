package gateway

import (
	"log/slog"
	"net/http"
	"strings"
	"time"

	"github.com/mojimich2015/cryptoscope/libs/go/ratelimit"
	"github.com/mojimich2015/cryptoscope/libs/go/tenant"
	"github.com/redis/go-redis/v9"
)

type responseWriter struct {
	http.ResponseWriter
	status int
	body   []byte
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.status = code
	rw.ResponseWriter.WriteHeader(code)
}

func (rw *responseWriter) Write(b []byte) (int, error) {
	rw.body = append(rw.body, b...)
	return rw.ResponseWriter.Write(b)
}

func LoggingMiddleware(logger *slog.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			rw := &responseWriter{ResponseWriter: w, status: http.StatusOK}
			next.ServeHTTP(rw, r)
			logger.Info("request",
				"method", r.Method,
				"path", r.URL.Path,
				"status", rw.status,
				"duration", time.Since(start).String(),
				"remote", r.RemoteAddr,
			)
		})
	}
}

func TenantMiddleware(logger *slog.Logger, devMode bool) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			tenantID := r.Header.Get("X-Tenant-Id")
			tenantSlug := r.Header.Get("X-Tenant-Slug")

			if tenantID == "" {
				if devMode {
					tenantID = "demo-tenant"
					tenantSlug = "demo"
				} else {
					// Protected routes resolve the tenant from a verified JWT claim.
					// Other routes still require tenant context when they need it.
					if strings.HasPrefix(r.URL.Path, "/v1/") {
						next.ServeHTTP(w, r)
						return
					}
					http.Error(w, `{"error":"tenant ID is required"}`, http.StatusBadRequest)
					return
				}
			}

			ident := tenant.Identity{ID: tenantID, Slug: tenantSlug}
			ctx := tenant.NewContext(r.Context(), ident)
			r = r.WithContext(ctx)

			logger.Debug("tenant resolved", "id", tenantID, "slug", tenantSlug)
			next.ServeHTTP(w, r)
		})
	}
}

func RateLimitMiddleware(limiter *ratelimit.Limiter, logger *slog.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			key := r.RemoteAddr
			if tid := r.Header.Get("X-Tenant-Id"); tid != "" {
				key = tid
			}

			allowed, err := limiter.Allow(r.Context(), key)
			if err != nil {
				logger.Error("rate limit check failed", "error", err)
				next.ServeHTTP(w, r)
				return
			}
			if !allowed {
				http.Error(w, `{"error":"rate limit exceeded"}`, http.StatusTooManyRequests)
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

func TenantForwardingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ident, err := tenant.FromContext(r.Context())
		if err == nil {
			r.Header.Set("X-Tenant-Id", ident.ID)
			r.Header.Set("X-Tenant-Slug", ident.Slug)
		}
		next.ServeHTTP(w, r)
	})
}

func NewRedisClient(addr, password string, db int) *redis.Client {
	return redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: password,
		DB:       db,
	})
}

func RecoveryMiddleware(logger *slog.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			defer func() {
				if rec := recover(); rec != nil {
					logger.Error("panic recovered", "error", rec)
					http.Error(w, `{"error":"internal server error"}`, http.StatusInternalServerError)
				}
			}()
			next.ServeHTTP(w, r)
		})
	}
}
