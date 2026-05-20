// Package logging provides a small wrapper around slog that emits structured
// JSON and carries the trace and tenant identifiers on every line.
//
// Centralized logging only pays off when every service logs the same shape, so
// this package is deliberately opinionated about the field names.
package logging

import (
	"context"
	"log/slog"
	"os"
	"strings"
)

type contextKey string

const (
	tenantKey contextKey = "tenant_id"
	traceKey  contextKey = "trace_id"
)

// New builds a JSON logger at the given level, tagged with the service name.
func New(service, level string) *slog.Logger {
	handler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: parseLevel(level),
	})
	return slog.New(handler).With(slog.String("service", service))
}

// WithTenant returns a context carrying the tenant identifier so downstream
// log calls can attach it automatically.
func WithTenant(ctx context.Context, tenantID string) context.Context {
	return context.WithValue(ctx, tenantKey, tenantID)
}

// WithTrace returns a context carrying the trace identifier.
func WithTrace(ctx context.Context, traceID string) context.Context {
	return context.WithValue(ctx, traceKey, traceID)
}

// FromContext enriches a logger with the tenant and trace identifiers found in
// the context. Missing values are simply skipped.
func FromContext(ctx context.Context, logger *slog.Logger) *slog.Logger {
	if v, ok := ctx.Value(tenantKey).(string); ok && v != "" {
		logger = logger.With(slog.String("tenant_id", v))
	}
	if v, ok := ctx.Value(traceKey).(string); ok && v != "" {
		logger = logger.With(slog.String("trace_id", v))
	}
	return logger
}

func parseLevel(level string) slog.Level {
	switch strings.ToLower(strings.TrimSpace(level)) {
	case "debug":
		return slog.LevelDebug
	case "warn", "warning":
		return slog.LevelWarn
	case "error":
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}
