package config

import (
	"os"
	"testing"
)

func TestLoadDefaults(t *testing.T) {
	cfg := Load()
	if cfg.HTTPPort != ":8080" {
		t.Fatalf("expected :8080, got %s", cfg.HTTPPort)
	}
	if cfg.MetricsPort != ":9101" {
		t.Fatalf("expected :9101, got %s", cfg.MetricsPort)
	}
	if cfg.GRPCAddr != "localhost:9001" {
		t.Fatalf("expected localhost:9001, got %s", cfg.GRPCAddr)
	}
	if cfg.CommandHTTP != "http://localhost:8002" {
		t.Fatalf("expected http://localhost:8002, got %s", cfg.CommandHTTP)
	}
	if cfg.RateLimitPerMinute != 120 {
		t.Fatalf("expected 120, got %d", cfg.RateLimitPerMinute)
	}
	if cfg.RateLimitBurst != 40 {
		t.Fatalf("expected 40, got %d", cfg.RateLimitBurst)
	}
}

func TestLoadFromEnv(t *testing.T) {
	os.Setenv("API_GATEWAY_HTTP_PORT", "9090")
	os.Setenv("QUERY_SERVICE_GRPC_ADDR", "query:9001")
	os.Setenv("COMMAND_SERVICE_HTTP_ADDR", "http://command:8002")
	os.Setenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "200")
	os.Setenv("RATE_LIMIT_BURST", "50")
	defer func() {
		os.Unsetenv("API_GATEWAY_HTTP_PORT")
		os.Unsetenv("QUERY_SERVICE_GRPC_ADDR")
		os.Unsetenv("COMMAND_SERVICE_HTTP_ADDR")
		os.Unsetenv("RATE_LIMIT_REQUESTS_PER_MINUTE")
		os.Unsetenv("RATE_LIMIT_BURST")
	}()

	cfg := Load()
	if cfg.HTTPPort != ":9090" {
		t.Fatalf("expected :9090, got %s", cfg.HTTPPort)
	}
	if cfg.GRPCAddr != "query:9001" {
		t.Fatalf("expected query:9001, got %s", cfg.GRPCAddr)
	}
	if cfg.CommandHTTP != "http://command:8002" {
		t.Fatalf("expected http://command:8002, got %s", cfg.CommandHTTP)
	}
	if cfg.RateLimitPerMinute != 200 {
		t.Fatalf("expected 200, got %d", cfg.RateLimitPerMinute)
	}
	if cfg.RateLimitBurst != 50 {
		t.Fatalf("expected 50, got %d", cfg.RateLimitBurst)
	}
}
