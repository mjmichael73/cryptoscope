package metrics

import (
	"testing"
)

func TestNewServer(t *testing.T) {
	s := NewServer(":9999")
	if s == nil {
		t.Fatal("expected non-nil server")
	}
}

func TestNewServerEmptyAddr(t *testing.T) {
	s := NewServer("")
	if s == nil {
		t.Fatal("expected non-nil server")
	}
}
