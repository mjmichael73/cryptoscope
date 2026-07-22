package tracing

import (
	"context"
	"testing"
)

func TestSetupWithInvalidEndpoint(t *testing.T) {
	shutdown, err := Setup(context.Background(), Config{
		ServiceName:  "test",
		Namespace:    "cryptoscope",
		OTLPEndpoint: "http://localhost:19999",
	})
	if err != nil {
		// Connection refused is expected for a random high port.
		// The important thing is that Setup doesn't panic.
		if shutdown != nil {
			t.Fatal("expected nil shutdown on error")
		}
	} else {
		if shutdown == nil {
			t.Fatal("expected non-nil shutdown on success")
		}
		defer shutdown(context.Background())
	}
}

func TestStripScheme(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"http://localhost:4317", "localhost:4317"},
		{"https://otel.example.com:4317", "otel.example.com:4317"},
		{"localhost:4317", "localhost:4317"},
		{"http://127.0.0.1:4317", "127.0.0.1:4317"},
		{"", ""},
	}
	for _, tc := range tests {
		got := stripScheme(tc.input)
		if got != tc.want {
			t.Fatalf("stripScheme(%q): expected %q, got %q", tc.input, tc.want, got)
		}
	}
}
