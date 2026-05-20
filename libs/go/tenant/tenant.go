// Package tenant carries the tenant identity through the call chain.
//
// Every tenant-scoped operation in the platform needs a tenant id, and getting
// it wrong is a data isolation bug, so we keep the plumbing in one place and
// make it hard to forget.
package tenant

import (
	"context"
	"errors"
)

// ErrMissing is returned when a tenant is required but absent from the context.
var ErrMissing = errors.New("tenant identity is missing from context")

type contextKey struct{}

// Identity describes the tenant a request belongs to.
type Identity struct {
	ID   string
	Slug string
}

// NewContext returns a context carrying the tenant identity.
func NewContext(ctx context.Context, id Identity) context.Context {
	return context.WithValue(ctx, contextKey{}, id)
}

// FromContext extracts the tenant identity, returning ErrMissing when it is not
// present or has an empty id.
func FromContext(ctx context.Context) (Identity, error) {
	id, ok := ctx.Value(contextKey{}).(Identity)
	if !ok || id.ID == "" {
		return Identity{}, ErrMissing
	}
	return id, nil
}
