// Package config loads the ingest service configuration from the environment.
package config

import (
	"time"

	shared "github.com/mojimich2015/cryptoscope/libs/go/config"
)

// Config holds everything the ingest service needs to run.
type Config struct {
	LogLevel string

	KafkaBrokers []string
	TicksTopic   string

	RedisAddr     string
	RedisPassword string
	RedisDB       int

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

		RedisAddr:     shared.Getenv("REDIS_ADDR", "localhost:6379"),
		RedisPassword: shared.Getenv("REDIS_PASSWORD", ""),
		RedisDB:       shared.GetenvInt("REDIS_DB", 0),

		BinanceBaseURL:  shared.Getenv("BINANCE_BASE_URL", "https://api.binance.com"),
		CoinbaseBaseURL: shared.Getenv("COINBASE_BASE_URL", "https://api.exchange.coinbase.com"),

		Symbols:      shared.GetenvList("INGEST_SYMBOLS", []string{"BTCUSDT", "ETHUSDT"}),
		PollInterval: shared.GetenvDuration("INGEST_POLL_INTERVAL_SECONDS", 15),

		OTLPEndpoint:  shared.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
		OTLPNamespace: shared.Getenv("OTEL_SERVICE_NAMESPACE", "cryptoscope"),
		MetricsAddr:   ":" + shared.Getenv("PROMETHEUS_METRICS_PORT", "9100"),
	}
}
