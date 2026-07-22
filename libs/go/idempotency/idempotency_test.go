package idempotency

import (
	"testing"
	"time"
)

func TestNewStore(t *testing.T) {
	s := NewStore(nil, "test", time.Hour)
	if s == nil {
		t.Fatal("expected non-nil store")
	}
	if s.prefix != "test" {
		t.Fatalf("expected prefix test, got %s", s.prefix)
	}
	if s.ttl != time.Hour {
		t.Fatalf("expected ttl 1h, got %v", s.ttl)
	}
}

func TestStorePrefixInKey(t *testing.T) {
	s := NewStore(nil, "myapp", time.Hour)
	if s.prefix != "myapp" {
		t.Fatalf("expected prefix myapp, got %s", s.prefix)
	}
}

func TestStoreDefaultTTL(t *testing.T) {
	s := NewStore(nil, "test", 24*time.Hour)
	if s.ttl != 24*time.Hour {
		t.Fatalf("expected ttl 24h, got %v", s.ttl)
	}
}
