package config

import (
	"time"

	shared "github.com/mojimich2015/cryptoscope/libs/go/config"
)

type Config struct {
	LogLevel string

	HTTPPort     string
	MetricsPort  string
	GRPCAddr     string
	CommandHTTP  string

	RedisAddr     string
	RedisPassword string
	RedisDB       int

	JWKSURL    string
	Issuer     string
	Audience   string

	RateLimitPerMinute int
	RateLimitBurst     int

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

		RedisAddr:     shared.Getenv("REDIS_ADDR", "localhost:6379"),
		RedisPassword: shared.Getenv("REDIS_PASSWORD", ""),
		RedisDB:       shared.GetenvInt("REDIS_DB", 0),

		JWKSURL:  shared.Getenv("KEYCLOAK_JWKS_URL", "http://localhost:8080/realms/cryptoscope/protocol/openid-connect/certs"),
		Issuer:   shared.Getenv("KEYCLOAK_ISSUER", "http://localhost:8080/realms/cryptoscope"),
		Audience: shared.Getenv("KEYCLOAK_AUDIENCE", "cryptoscope-api"),

		RateLimitPerMinute: shared.GetenvInt("RATE_LIMIT_REQUESTS_PER_MINUTE", 120),
		RateLimitBurst:     shared.GetenvInt("RATE_LIMIT_BURST", 40),

		OTLPEndpoint:  shared.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
		OTLPNamespace: shared.Getenv("OTEL_SERVICE_NAMESPACE", "cryptoscope"),
	}
}

func (c *Config) RateLimitRefresh() time.Duration {
	return time.Duration(60 / c.RateLimitPerMinute) * time.Second
}
