package source

import (
	"testing"
)

func TestParseFloatValid(t *testing.T) {
	v, err := parseFloat("123.456")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if v != 123.456 {
		t.Fatalf("expected 123.456, got %f", v)
	}
}

func TestParseFloatInteger(t *testing.T) {
	v, err := parseFloat("42")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if v != 42.0 {
		t.Fatalf("expected 42.0, got %f", v)
	}
}

func TestParseFloatInvalid(t *testing.T) {
	_, err := parseFloat("not-a-number")
	if err == nil {
		t.Fatal("expected error for invalid input")
	}
}

func TestParseFloatEmpty(t *testing.T) {
	_, err := parseFloat("")
	if err == nil {
		t.Fatal("expected error for empty string")
	}
}

func TestParseFloatNegative(t *testing.T) {
	v, err := parseFloat("-5.5")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if v != -5.5 {
		t.Fatalf("expected -5.5, got %f", v)
	}
}
