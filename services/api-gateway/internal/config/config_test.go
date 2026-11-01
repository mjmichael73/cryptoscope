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

func TestValidateRequiresKeycloakWhenAuthEnabled(t *testing.T) {
	cfg := Config{}
	if err := cfg.Validate("development"); err == nil {
		t.Fatal("expected missing Keycloak settings to fail validation")
	}
	cfg = Config{JWKSURL: "http://keycloak:8080/jwks", Issuer: "http://keycloak:8080/realm", Audience: "api"}
	if err := cfg.Validate("development"); err != nil {
		t.Fatalf("expected valid auth config, got %v", err)
	}
}

func TestValidateRejectsDevModeInProduction(t *testing.T) {
	cfg := Config{DevMode: true}
	if err := cfg.Validate("production"); err == nil {
		t.Fatal("expected DEV_MODE to be rejected in production")
	}
	if err := cfg.Validate("Production"); err == nil {
		t.Fatal("expected case-insensitive production environment to reject DEV_MODE")
	}
}

func TestValidateRejectsInvalidJWKSURL(t *testing.T) {
	cfg := Config{JWKSURL: "/jwks", Issuer: "http://keycloak/realm", Audience: "api"}
	if err := cfg.Validate("production"); err == nil {
		t.Fatal("expected relative JWKS URL to fail validation")
	}
}

func TestValidateRedisProductionRequirements(t *testing.T) {
	cfg := Config{
		RedisPassword:     "secret",
		RedisPasswordFile: true,
		JWKSURL:           "https://keycloak.example/keys",
		Issuer:            "https://keycloak.example/realm",
		Audience:          "cryptoscope",
	}
	if err := cfg.Validate("production"); err == nil {
		t.Fatal("expected production Redis TLS to be required")
	}
	cfg.RedisTLS = true
	cfg.RedisPasswordFile = false
	if err := cfg.Validate("production"); err == nil {
		t.Fatal("expected production Redis password to come from a secret file")
	}
	cfg.RedisPasswordFile = true
	if err := cfg.Validate("production"); err != nil {
		t.Fatalf("expected secure Redis config to validate, got %v", err)
	}
}

func TestParseBoolEnv(t *testing.T) {
	for _, tc := range []struct {
		value string
		want  bool
	}{{"true", true}, {"TRUE", true}, {"1", true}, {"false", false}, {"invalid", false}} {
		if got := ParseBoolEnv(tc.value); got != tc.want {
			t.Errorf("ParseBoolEnv(%q) = %t, want %t", tc.value, got, tc.want)
		}
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
