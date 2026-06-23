package auth

import (
	"context"
	"crypto/rsa"
	"crypto/x509"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"math/big"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

type KeyStore interface {
	KeyFunc(ctx context.Context) jwt.Keyfunc
	Refresh(ctx context.Context) error
}

type JWKS struct {
	Keys []JWK `json:"keys"`
}

type JWK struct {
	KID string `json:"kid"`
	KTY string `json:"kty"`
	ALG string `json:"alg"`
	N   string `json:"n"`
	E   string `json:"e"`
}

type CachingKeyStore struct {
	mu       sync.RWMutex
	url      string
	issuer   string
	audience string
	client   *http.Client
	keys     map[string]*rsa.PublicKey
}

func NewKeyStore(jwksURL, issuer, audience string) *CachingKeyStore {
	return &CachingKeyStore{
		url:      jwksURL,
		issuer:   issuer,
		audience: audience,
		client:   &http.Client{Timeout: 10 * time.Second},
		keys:     make(map[string]*rsa.PublicKey),
	}
}

func (s *CachingKeyStore) Refresh(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, s.url, nil)
	if err != nil {
		return fmt.Errorf("jwks request: %w", err)
	}
	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("jwks fetch: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("jwks fetch: status %d", resp.StatusCode)
	}

	var jwks JWKS
	if err := json.NewDecoder(resp.Body).Decode(&jwks); err != nil {
		return fmt.Errorf("jwks decode: %w", err)
	}

	keys := make(map[string]*rsa.PublicKey, len(jwks.Keys))
	for _, k := range jwks.Keys {
		if k.KTY != "RSA" {
			continue
		}
		pub, err := decodeRSAPublicKey(k.N, k.E)
		if err != nil {
			continue
		}
		keys[k.KID] = pub
	}

	s.mu.Lock()
	s.keys = keys
	s.mu.Unlock()
	return nil
}

func (s *CachingKeyStore) KeyFunc(ctx context.Context) jwt.Keyfunc {
	return func(token *jwt.Token) (any, error) {
		if _, ok := token.Method.(*jwt.SigningMethodRSA); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}

		kid, ok := token.Header["kid"].(string)
		if !ok {
			return nil, fmt.Errorf("kid missing from token header")
		}

		s.mu.RLock()
		key, ok := s.keys[kid]
		s.mu.RUnlock()
		if !ok {
			if err := s.Refresh(ctx); err != nil {
				return nil, fmt.Errorf("key refresh failed: %w", err)
			}
			s.mu.RLock()
			key, ok = s.keys[kid]
			s.mu.RUnlock()
			if !ok {
				return nil, fmt.Errorf("key %s not found in JWKS", kid)
			}
		}
		return key, nil
	}
}

func (s *CachingKeyStore) Validate(ctx context.Context, rawToken string) (*jwt.MapClaims, error) {
	token, err := jwt.Parse(rawToken, s.KeyFunc(ctx),
		jwt.WithIssuer(s.issuer),
		jwt.WithAudience(s.audience),
		jwt.WithValidMethods([]string{"RS256"}),
	)
	if err != nil {
		return nil, fmt.Errorf("token validation: %w", err)
	}
	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return nil, fmt.Errorf("unexpected claims type")
	}
	return &claims, nil
}

func decodeRSAPublicKey(n, e string) (*rsa.PublicKey, error) {
	nd, err := base64.RawURLEncoding.DecodeString(n)
	if err != nil {
		return nil, fmt.Errorf("decode n: %w", err)
	}
	ed, err := base64.RawURLEncoding.DecodeString(e)
	if err != nil {
		return nil, fmt.Errorf("decode e: %w", err)
	}

	var exp int
	if len(ed) < 8 {
		buf := make([]byte, 8)
		copy(buf[8-len(ed):], ed)
		exp = int(binary.BigEndian.Uint64(buf))
	} else {
		exp = int(binary.BigEndian.Uint64(ed[:8]))
	}

	pub := &rsa.PublicKey{
		N: new(big.Int).SetBytes(nd),
		E: exp,
	}
	if _, err := x509.MarshalPKIXPublicKey(pub); err != nil {
		return nil, fmt.Errorf("invalid RSA key: %w", err)
	}
	return pub, nil
}

type contextKey string

const claimsKey contextKey = "auth.claims"

func WithClaims(ctx context.Context, claims *jwt.MapClaims) context.Context {
	return context.WithValue(ctx, claimsKey, claims)
}

func ClaimsFrom(ctx context.Context) (*jwt.MapClaims, bool) {
	c, ok := ctx.Value(claimsKey).(*jwt.MapClaims)
	return c, ok
}

func ExtractTenantID(claims *jwt.MapClaims) string {
	if tid, ok := (*claims)["tenant_id"].(string); ok {
		return tid
	}
	if tid, ok := (*claims)["sub"].(string); ok {
		return tid
	}
	return ""
}

func ExtractTenantSlug(claims *jwt.MapClaims) string {
	if slug, ok := (*claims)["tenant_slug"].(string); ok {
		return slug
	}
	if preferred, ok := (*claims)["preferred_username"].(string); ok {
		return preferred
	}
	return ""
}

func AuthMiddleware(keystore *CachingKeyStore) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			auth := r.Header.Get("Authorization")
			if auth == "" {
				http.Error(w, `{"error":"missing authorization header"}`, http.StatusUnauthorized)
				return
			}

			parts := strings.SplitN(auth, " ", 2)
			if len(parts) != 2 || !strings.EqualFold(parts[0], "bearer") {
				http.Error(w, `{"error":"invalid authorization format"}`, http.StatusUnauthorized)
				return
			}

			claims, err := keystore.Validate(r.Context(), parts[1])
			if err != nil {
				http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusUnauthorized)
				return
			}

			ctx := WithClaims(r.Context(), claims)
			r = r.WithContext(ctx)
			next.ServeHTTP(w, r)
		})
	}
}
