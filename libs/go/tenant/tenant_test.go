package tenant

import (
	"context"
	"errors"
	"testing"
)

func TestFromContextMissing(t *testing.T) {
	if _, err := FromContext(context.Background()); !errors.Is(err, ErrMissing) {
		t.Fatalf("expected ErrMissing, got %v", err)
	}
}

func TestRoundTrip(t *testing.T) {
	ctx := NewContext(context.Background(), Identity{ID: "t-1", Slug: "acme"})
	got, err := FromContext(ctx)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.ID != "t-1" || got.Slug != "acme" {
		t.Fatalf("unexpected identity: %+v", got)
	}
}

func TestEmptyIDIsMissing(t *testing.T) {
	ctx := NewContext(context.Background(), Identity{ID: ""})
	if _, err := FromContext(ctx); !errors.Is(err, ErrMissing) {
		t.Fatalf("expected ErrMissing for empty id, got %v", err)
	}
}
