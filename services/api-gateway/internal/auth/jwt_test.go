package auth

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/golang-jwt/jwt/v5"
)

func TestExtractTenantIDFromClaims(t *testing.T) {
	claims := jwt.MapClaims{"tenant_id": "tenant-1"}
	if got := ExtractTenantID(&claims); got != "tenant-1" {
		t.Fatalf("expected tenant-1, got %s", got)
	}
}

func TestExtractTenantIDFallsBackToSub(t *testing.T) {
	claims := jwt.MapClaims{"sub": "user-1"}
	if got := ExtractTenantID(&claims); got != "user-1" {
		t.Fatalf("expected user-1, got %s", got)
	}
}

func TestExtractTenantIDEmptyWhenMissing(t *testing.T) {
	claims := jwt.MapClaims{}
	if got := ExtractTenantID(&claims); got != "" {
		t.Fatalf("expected empty, got %s", got)
	}
}

func TestExtractTenantSlugFromClaims(t *testing.T) {
	claims := jwt.MapClaims{"tenant_slug": "acme-corp"}
	if got := ExtractTenantSlug(&claims); got != "acme-corp" {
		t.Fatalf("expected acme-corp, got %s", got)
	}
}

func TestExtractTenantSlugFallsBackToPreferredUsername(t *testing.T) {
	claims := jwt.MapClaims{"preferred_username": "acme"}
	if got := ExtractTenantSlug(&claims); got != "acme" {
		t.Fatalf("expected acme, got %s", got)
	}
}

func TestWithClaimsAndClaimsFromRoundTrip(t *testing.T) {
	claims := jwt.MapClaims{"tenant_id": "t1"}
	ctx := WithClaims(context.Background(), &claims)
	got, ok := ClaimsFrom(ctx)
	if !ok {
		t.Fatal("expected claims in context")
	}
	if (*got)["tenant_id"] != "t1" {
		t.Fatalf("expected t1, got %v", *got)
	}
}

func TestClaimsFromMissing(t *testing.T) {
	_, ok := ClaimsFrom(context.Background())
	if ok {
		t.Fatal("expected no claims from bare context")
	}
}

func TestAuthMiddlewareRejectsMissingHeader(t *testing.T) {
	ks := NewKeyStore("http://example.com/jwks", "issuer", "audience")
	handler := AuthMiddleware(ks)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", w.Code)
	}
}

func TestAuthMiddlewareRejectsBadFormat(t *testing.T) {
	ks := NewKeyStore("http://example.com/jwks", "issuer", "audience")
	handler := AuthMiddleware(ks)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set("Authorization", "NotBearer token123")
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", w.Code)
	}
}

func TestAuthMiddlewareRejectsInvalidToken(t *testing.T) {
	ks := NewKeyStore("http://example.com/jwks", "issuer", "audience")
	handler := AuthMiddleware(ks)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set("Authorization", "Bearer invalid-token")
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", w.Code)
	}
}

func TestNewKeyStoreInitializesEmptyKeys(t *testing.T) {
	ks := NewKeyStore("http://example.com/jwks", "issuer", "audience")
	if ks == nil {
		t.Fatal("expected non-nil keystore")
	}
}
