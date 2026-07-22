package ratelimit

import (
	"testing"

	"github.com/redis/go-redis/v9"
)

func TestNew(t *testing.T) {
	l := New(nil, 120, 40)
	if l == nil {
		t.Fatal("expected non-nil limiter")
	}
	if l.capacity != 40 {
		t.Fatalf("expected capacity 40, got %d", l.capacity)
	}
	if l.refill != 2.0 {
		t.Fatalf("expected refill 2.0, got %f", l.refill)
	}
}

func TestNewZeroValues(t *testing.T) {
	l := New(nil, 0, 0)
	if l.capacity != 0 {
		t.Fatalf("expected capacity 0, got %d", l.capacity)
	}
}

func TestNewCalculatesRefillCorrectly(t *testing.T) {
	l := New(&redis.Client{}, 60, 10)
	if l.capacity != 10 {
		t.Fatalf("expected capacity 10, got %d", l.capacity)
	}
	if l.refill != 1.0 {
		t.Fatalf("expected refill 1.0 (60/60), got %f", l.refill)
	}
}

func TestNewCalculatesRefillFor200PerMin(t *testing.T) {
	l := New(&redis.Client{}, 200, 50)
	if l.capacity != 50 {
		t.Fatalf("expected capacity 50, got %d", l.capacity)
	}
	if l.refill != 200.0/60.0 {
		t.Fatalf("expected refill %f, got %f", 200.0/60.0, l.refill)
	}
}
