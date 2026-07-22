package config

import (
	"os"
	"testing"
)

func TestLoadDefaults(t *testing.T) {
	cfg := Load()
	if cfg.LogLevel != "info" {
		t.Fatalf("expected info, got %s", cfg.LogLevel)
	}
	if len(cfg.KafkaBrokers) == 0 {
		t.Fatal("expected kafka brokers")
	}
	if len(cfg.Intervals) == 0 {
		t.Fatal("expected intervals")
	}
}

func TestLoadFromEnv(t *testing.T) {
	os.Setenv("LOG_LEVEL", "debug")
	os.Setenv("KAFKA_BROKERS", "broker1:9092,broker2:9092")
	os.Setenv("PROCESSOR_INTERVALS", "1m,5m,1h,15m")
	os.Setenv("PLATFORM_TENANT_ID", "test-tenant")
	defer func() {
		os.Unsetenv("LOG_LEVEL")
		os.Unsetenv("KAFKA_BROKERS")
		os.Unsetenv("PROCESSOR_INTERVALS")
		os.Unsetenv("PLATFORM_TENANT_ID")
	}()

	cfg := Load()
	if cfg.LogLevel != "debug" {
		t.Fatalf("expected debug, got %s", cfg.LogLevel)
	}
	if cfg.TenantID != "test-tenant" {
		t.Fatalf("expected test-tenant, got %s", cfg.TenantID)
	}
	if len(cfg.KafkaBrokers) != 2 {
		t.Fatalf("expected 2 brokers, got %d", len(cfg.KafkaBrokers))
	}
}
