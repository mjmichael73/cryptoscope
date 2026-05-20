package config

import (
	"testing"
	"time"
)

func TestGetenvFallback(t *testing.T) {
	t.Setenv("CS_TEST_KEY", "")
	if got := Getenv("CS_TEST_KEY", "fallback"); got != "fallback" {
		t.Fatalf("expected fallback, got %q", got)
	}
	t.Setenv("CS_TEST_KEY", "value")
	if got := Getenv("CS_TEST_KEY", "fallback"); got != "value" {
		t.Fatalf("expected value, got %q", got)
	}
}

func TestGetenvIntInvalidFallsBack(t *testing.T) {
	t.Setenv("CS_TEST_INT", "not-a-number")
	if got := GetenvInt("CS_TEST_INT", 42); got != 42 {
		t.Fatalf("expected 42, got %d", got)
	}
}

func TestGetenvDuration(t *testing.T) {
	t.Setenv("CS_TEST_DUR", "30")
	if got := GetenvDuration("CS_TEST_DUR", 5); got != 30*time.Second {
		t.Fatalf("expected 30s, got %s", got)
	}
}

func TestGetenvListTrimsAndSkipsEmpty(t *testing.T) {
	t.Setenv("CS_TEST_LIST", " BTCUSDT , ,ETHUSDT ")
	got := GetenvList("CS_TEST_LIST", nil)
	want := []string{"BTCUSDT", "ETHUSDT"}
	if len(got) != len(want) {
		t.Fatalf("expected %v, got %v", want, got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("index %d: expected %q, got %q", i, want[i], got[i])
		}
	}
}

func TestMustGetenvMissing(t *testing.T) {
	if _, err := MustGetenv("CS_TEST_DEFINITELY_UNSET"); err == nil {
		t.Fatal("expected an error for a missing variable")
	}
}
