package auth

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"encoding/base64"
	"encoding/json"
	"math/big"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

func TestExtractTenantIDFromClaims(t *testing.T) {
	claims := jwt.MapClaims{"tenant_id": "tenant-1"}
	if got := ExtractTenantID(&claims); got != "tenant-1" {
		t.Fatalf("expected tenant-1, got %s", got)
	}
}

func TestExtractTenantIDDoesNotUseSubjectAsTenant(t *testing.T) {
	claims := jwt.MapClaims{"sub": "user-1"}
	if got := ExtractTenantID(&claims); got != "" {
		t.Fatalf("expected no tenant id, got %s", got)
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

func TestValidateRequiresTenantIDAndChecksKeycloakClaims(t *testing.T) {
	privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	encode := func(n *big.Int) string { return base64.RawURLEncoding.EncodeToString(n.Bytes()) }
	publicE := big.NewInt(int64(privateKey.PublicKey.E)).Bytes()
	encodeE := base64.RawURLEncoding.EncodeToString(publicE)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(JWKS{Keys: []JWK{{KID: "key-1", KTY: "RSA", ALG: "RS256", N: encode(privateKey.PublicKey.N), E: encodeE}}})
	}))
	defer server.Close()
	ks := NewKeyStore(server.URL, "https://issuer.example/realm", "cryptoscope-api")
	tokenFor := func(claims jwt.MapClaims) string {
		t.Helper()
		token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
		token.Header["kid"] = "key-1"
		signed, err := token.SignedString(privateKey)
		if err != nil {
			t.Fatal(err)
		}
		return signed
	}
	base := jwt.MapClaims{"iss": "https://issuer.example/realm", "aud": "cryptoscope-api", "exp": time.Now().Add(time.Minute).Unix()}
	withTenant := jwt.MapClaims{"iss": base["iss"], "aud": base["aud"], "exp": base["exp"], "tenant_id": "tenant-1"}
	claims, err := ks.Validate(context.Background(), tokenFor(withTenant))
	if err != nil {
		t.Fatalf("valid token rejected: %v", err)
	}
	if got := ExtractTenantID(claims); got != "tenant-1" {
		t.Fatalf("expected tenant-1, got %q", got)
	}

	withoutTenant := jwt.MapClaims{"iss": base["iss"], "aud": base["aud"], "exp": base["exp"], "sub": "user-1"}
	if _, err := ks.Validate(context.Background(), tokenFor(withoutTenant)); err == nil {
		t.Fatal("expected token without tenant_id to be rejected")
	}
	wrongIssuer := jwt.MapClaims{"iss": "https://wrong.example", "aud": base["aud"], "exp": base["exp"], "tenant_id": "tenant-1"}
	if _, err := ks.Validate(context.Background(), tokenFor(wrongIssuer)); err == nil {
		t.Fatal("expected token with wrong issuer to be rejected")
	}
}

func TestRefreshRejectsJWKSWithoutUsableKeys(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`{"keys":[]}`))
	}))
	defer server.Close()
	ks := NewKeyStore(server.URL, "https://issuer.example/realm", "cryptoscope-api")
	if err := ks.Refresh(context.Background()); err == nil {
		t.Fatal("expected empty JWKS to be rejected")
	}
}
