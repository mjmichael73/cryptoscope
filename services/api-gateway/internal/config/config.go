package config

import (
	"fmt"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	shared "github.com/mojimich2015/cryptoscope/libs/go/config"
)

type Config struct {
	LogLevel string
	DevMode  bool

	HTTPPort    string
	MetricsPort string
	GRPCAddr    string
	CommandHTTP string
	AlertHTTP   string

	RedisAddr         string
	RedisPassword     string
	RedisPasswordFile bool
	RedisDB           int
	RedisTLS          bool

	JWKSURL  string
	Issuer   string
	Audience string

	RateLimitPerMinute int
	RateLimitBurst     int

	CORSAllowedOrigins []string

	OTLPEndpoint  string
	OTLPNamespace string
}

func Load() Config {
	return Config{
		LogLevel: shared.Getenv("LOG_LEVEL", "info"),

		HTTPPort:    ":" + shared.Getenv("API_GATEWAY_HTTP_PORT", "8080"),
		MetricsPort: ":" + shared.Getenv("PROMETHEUS_METRICS_PORT", "9101"),
		GRPCAddr:    shared.Getenv("QUERY_SERVICE_GRPC_ADDR", "localhost:9001"),
		CommandHTTP: shared.Getenv("COMMAND_SERVICE_HTTP_ADDR", "http://localhost:8002"),
		AlertHTTP:   shared.Getenv("ALERT_SERVICE_HTTP_ADDR", "http://localhost:8003"),

		RedisAddr:         shared.Getenv("REDIS_ADDR", "localhost:6379"),
		RedisPassword:     shared.GetenvSecret("REDIS_PASSWORD", ""),
		RedisPasswordFile: strings.TrimSpace(os.Getenv("REDIS_PASSWORD_FILE")) != "",
		RedisDB:           shared.GetenvInt("REDIS_DB", 0),
		RedisTLS:          ParseBoolEnv(shared.Getenv("REDIS_TLS_ENABLED", "false")),

		DevMode: shared.Getenv("DEV_MODE", "false") == "true",

		JWKSURL:  shared.Getenv("KEYCLOAK_JWKS_URL", "http://localhost:8080/realms/cryptoscope/protocol/openid-connect/certs"),
		Issuer:   shared.Getenv("KEYCLOAK_ISSUER", "http://localhost:8080/realms/cryptoscope"),
		Audience: shared.Getenv("KEYCLOAK_AUDIENCE", "cryptoscope-api"),

		RateLimitPerMinute: shared.GetenvInt("RATE_LIMIT_REQUESTS_PER_MINUTE", 120),
		RateLimitBurst:     shared.GetenvInt("RATE_LIMIT_BURST", 40),

		CORSAllowedOrigins: parseCORSOrigins(shared.Getenv("CORS_ALLOWED_ORIGINS", "")),

		OTLPEndpoint:  shared.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
		OTLPNamespace: shared.Getenv("OTEL_SERVICE_NAMESPACE", "cryptoscope"),
	}
}

// Validate rejects configurations that could disable authentication or make
// JWT verification impossible. Development mode is only permitted outside
// explicitly production environments.
func (c Config) Validate(environment string) error {
	if strings.EqualFold(strings.TrimSpace(environment), "production") {
		if !c.RedisPasswordFile || strings.TrimSpace(c.RedisPassword) == "" {
			return fmt.Errorf("REDIS_PASSWORD_FILE is required in production")
		}
		if !c.RedisTLS {
			return fmt.Errorf("REDIS_TLS_ENABLED must be true in production")
		}
	}
	if strings.EqualFold(strings.TrimSpace(environment), "production") && c.DevMode {
		return fmt.Errorf("DEV_MODE must be disabled in production")
	}
	if c.DevMode {
		return nil
	}
	for _, setting := range []struct{ name, value string }{
		{"KEYCLOAK_JWKS_URL", c.JWKSURL},
		{"KEYCLOAK_ISSUER", c.Issuer},
		{"KEYCLOAK_AUDIENCE", c.Audience},
	} {
		name, value := setting.name, setting.value
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("%s is required when DEV_MODE is disabled", name)
		}
	}
	u, err := url.ParseRequestURI(c.JWKSURL)
	if err != nil || u.Host == "" || (u.Scheme != "https" && u.Scheme != "http") {
		return fmt.Errorf("KEYCLOAK_JWKS_URL must be an absolute HTTP(S) URL")
	}
	issuer, err := url.ParseRequestURI(c.Issuer)
	if err != nil || issuer.Host == "" || (issuer.Scheme != "https" && issuer.Scheme != "http") {
		return fmt.Errorf("KEYCLOAK_ISSUER must be an absolute HTTP(S) URL")
	}
	return nil
}

// ParseBoolEnv is a strict helper for boolean environment settings. Invalid
// values are false so production validation fails closed.
func ParseBoolEnv(value string) bool {
	parsed, err := strconv.ParseBool(strings.TrimSpace(value))
	return err == nil && parsed
}

func (c *Config) RateLimitRefresh() time.Duration {
	return time.Duration(60/c.RateLimitPerMinute) * time.Second
}

func parseCORSOrigins(raw string) []string {
	if raw == "" {
		return nil
	}
	origins := make([]string, 0)
	for _, o := range strings.Split(raw, ",") {
		o = strings.TrimSpace(o)
		if o != "" {
			origins = append(origins, o)
		}
	}
	return origins
}
