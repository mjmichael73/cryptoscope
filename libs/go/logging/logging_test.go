package logging

import (
	"context"
	"log/slog"
	"strings"
	"testing"
)

func TestNew(t *testing.T) {
	logger := New("test-service", "info")
	if logger == nil {
		t.Fatal("expected non-nil logger")
	}
}

func TestNewWithDebugLevel(t *testing.T) {
	logger := New("test-service", "debug")
	if logger == nil {
		t.Fatal("expected non-nil logger")
	}
}

func TestNewWithWarnLevel(t *testing.T) {
	logger := New("test-service", "warn")
	if logger == nil {
		t.Fatal("expected non-nil logger")
	}
}

func TestNewWithErrorLevel(t *testing.T) {
	logger := New("test-service", "error")
	if logger == nil {
		t.Fatal("expected non-nil logger")
	}
}

func TestNewWithInvalidLevelDefaultsToInfo(t *testing.T) {
	logger := New("test-service", "invalid")
	if logger == nil {
		t.Fatal("expected non-nil logger")
	}
}

func TestWithTenantAddsToContext(t *testing.T) {
	ctx := WithTenant(context.Background(), "tenant-1")
	// FromContext should enrich a logger with the tenant ID
	var buf strings.Builder
	h := slog.NewTextHandler(&buf, &slog.HandlerOptions{Level: slog.LevelInfo})
	logger := slog.New(h)
	enriched := FromContext(ctx, logger)
	enriched.Info("test")
	output := buf.String()
	if !strings.Contains(output, "tenant-1") {
		t.Fatalf("expected tenant-1 in log output, got: %s", output)
	}
}

func TestWithTraceAddsToContext(t *testing.T) {
	ctx := WithTrace(context.Background(), "trace-123")
	var buf strings.Builder
	h := slog.NewTextHandler(&buf, &slog.HandlerOptions{Level: slog.LevelInfo})
	logger := slog.New(h)
	enriched := FromContext(ctx, logger)
	enriched.Info("test")
	output := buf.String()
	if !strings.Contains(output, "trace-123") {
		t.Fatalf("expected trace-123 in log output, got: %s", output)
	}
}

func TestWithTenantAndTrace(t *testing.T) {
	ctx := WithTenant(context.Background(), "tenant-1")
	ctx = WithTrace(ctx, "trace-abc")

	var buf strings.Builder
	h := slog.NewTextHandler(&buf, &slog.HandlerOptions{Level: slog.LevelInfo})
	logger := slog.New(h)
	enriched := FromContext(ctx, logger)
	enriched.Info("test")

	output := buf.String()
	if !strings.Contains(output, "tenant-1") || !strings.Contains(output, "trace-abc") {
		t.Fatalf("expected both tenant and trace in output, got: %s", output)
	}
}

func TestFromContextWithoutTenantOrTrace(t *testing.T) {
	var buf strings.Builder
	h := slog.NewTextHandler(&buf, &slog.HandlerOptions{Level: slog.LevelInfo})
	logger := slog.New(h)

	enriched := FromContext(context.Background(), logger)
	enriched.Info("test")

	if !strings.Contains(buf.String(), "test") {
		t.Fatal("expected logger to work without tenant/trace")
	}
}

func TestFromContextReturnsLogger(t *testing.T) {
	logger := New("test-service", "info")
	enriched := FromContext(context.Background(), logger)
	if enriched == nil {
		t.Fatal("expected non-nil logger")
	}
}

func TestParseLevel(t *testing.T) {
	tests := []struct {
		input string
		want  slog.Level
	}{
		{"debug", slog.LevelDebug},
		{"info", slog.LevelInfo},
		{"warn", slog.LevelWarn},
		{"error", slog.LevelError},
		{"invalid", slog.LevelInfo},
	}
	for _, tc := range tests {
		got := parseLevel(tc.input)
		if got != tc.want {
			t.Fatalf("parseLevel(%q): expected %d, got %d", tc.input, tc.want, got)
		}
	}
}
