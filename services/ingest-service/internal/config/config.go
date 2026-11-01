// Package config loads the ingest service configuration from the environment.
package config

import (
	"fmt"
	"os"
	"strings"
	"time"

	shared "github.com/mojimich2015/cryptoscope/libs/go/config"
)

// Config holds everything the ingest service needs to run.
type Config struct {
	LogLevel string

	KafkaBrokers []string
	TicksTopic   string

	RedisAddr         string
	RedisPassword     string
	RedisPasswordFile bool
	RedisDB           int
	RedisTLS          bool

	BinanceBaseURL  string
	CoinbaseBaseURL string

	Symbols      []string
	PollInterval time.Duration

	OTLPEndpoint  string
	OTLPNamespace string
	MetricsAddr   string
}

// Load reads the configuration, applying sensible local defaults.
func Load() Config {
	return Config{
		LogLevel: shared.Getenv("LOG_LEVEL", "info"),

		KafkaBrokers: shared.GetenvList("KAFKA_BROKERS", []string{"localhost:9092"}),
		TicksTopic:   shared.Getenv("KAFKA_TOPIC_TICKS", "market.ticks.raw"),

		RedisAddr:         shared.Getenv("REDIS_ADDR", "localhost:6379"),
		RedisPassword:     shared.GetenvSecret("REDIS_PASSWORD", ""),
		RedisPasswordFile: strings.TrimSpace(os.Getenv("REDIS_PASSWORD_FILE")) != "",
		RedisDB:           shared.GetenvInt("REDIS_DB", 0),
		RedisTLS:          strings.EqualFold(strings.TrimSpace(shared.Getenv("REDIS_TLS_ENABLED", "false")), "true"),

		BinanceBaseURL:  shared.Getenv("BINANCE_BASE_URL", "https://api.binance.com"),
		CoinbaseBaseURL: shared.Getenv("COINBASE_BASE_URL", "https://api.exchange.coinbase.com"),

		Symbols:      shared.GetenvList("INGEST_SYMBOLS", []string{"BTCUSDT", "ETHUSDT"}),
		PollInterval: shared.GetenvDuration("INGEST_POLL_INTERVAL_SECONDS", 15),

		OTLPEndpoint:  shared.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
		OTLPNamespace: shared.Getenv("OTEL_SERVICE_NAMESPACE", "cryptoscope"),
		MetricsAddr:   ":" + shared.Getenv("PROMETHEUS_METRICS_PORT", "9100"),
	}
}

// Validate rejects unsecured Redis settings in production deployments.
func (c Config) Validate(environment string) error {
	if strings.EqualFold(strings.TrimSpace(environment), "production") {
		if !c.RedisPasswordFile || strings.TrimSpace(c.RedisPassword) == "" {
			return fmt.Errorf("REDIS_PASSWORD_FILE is required in production")
		}
		if !c.RedisTLS {
			return fmt.Errorf("REDIS_TLS_ENABLED must be true in production")
		}
	}
	return nil
}
