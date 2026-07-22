package client

import (
	"testing"

	cryptov1 "github.com/mojimich2015/cryptoscope/proto/cryptoscope/v1"
)

func TestIntervalFromStringDefaultsTo1m(t *testing.T) {
	if got := intervalFromString(""); got != cryptov1.Interval_INTERVAL_1M {
		t.Fatalf("expected INTERVAL_1M, got %v", got)
	}
}

func TestIntervalFromStringUnknownDefaultsTo1m(t *testing.T) {
	if got := intervalFromString("invalid"); got != cryptov1.Interval_INTERVAL_1M {
		t.Fatalf("expected INTERVAL_1M, got %v", got)
	}
}

func TestIntervalFromString1m(t *testing.T) {
	if got := intervalFromString("1m"); got != cryptov1.Interval_INTERVAL_1M {
		t.Fatalf("expected INTERVAL_1M, got %v", got)
	}
}

func TestIntervalFromString5m(t *testing.T) {
	if got := intervalFromString("5m"); got != cryptov1.Interval_INTERVAL_5M {
		t.Fatalf("expected INTERVAL_5M, got %v", got)
	}
}

func TestIntervalFromString1h(t *testing.T) {
	if got := intervalFromString("1h"); got != cryptov1.Interval_INTERVAL_1H {
		t.Fatalf("expected INTERVAL_1H, got %v", got)
	}
}

func TestIntervalFromString1d(t *testing.T) {
	if got := intervalFromString("1d"); got != cryptov1.Interval_INTERVAL_1D {
		t.Fatalf("expected INTERVAL_1D, got %v", got)
	}
}
