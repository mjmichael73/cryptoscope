package config

import "testing"

func TestValidateRedisProductionRequirements(t *testing.T) {
	cfg := Config{RedisPassword: "secret", RedisPasswordFile: true}
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
	if err := (Config{}).Validate("local"); err != nil {
		t.Fatalf("expected local development config to validate, got %v", err)
	}
}
