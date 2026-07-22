// Package config loads the stream processor configuration from the environment.
package config

import shared "github.com/mojimich2015/cryptoscope/libs/go/config"

// Config holds everything the stream processor needs to run.
type Config struct {
	LogLevel string

	KafkaBrokers  []string
	TicksTopic    string
	ConsumerGroup string

	MongoURI string
	MongoDB  string

	ClickHouseAddr     string
	ClickHouseDB       string
	ClickHouseUser     string
	ClickHousePassword string

	Intervals []string
	TenantID  string

	OTLPEndpoint  string
	OTLPNamespace string
	MetricsAddr   string
}

// Load reads the configuration with local defaults.
func Load() Config {
	return Config{
		LogLevel: shared.Getenv("LOG_LEVEL", "info"),

		KafkaBrokers:  shared.GetenvList("KAFKA_BROKERS", []string{"localhost:9092"}),
		TicksTopic:    shared.Getenv("KAFKA_TOPIC_TICKS", "market.ticks.raw"),
		ConsumerGroup: shared.Getenv("KAFKA_CONSUMER_GROUP", "cryptoscope") + "-processor",

		MongoURI: shared.Getenv("MONGO_URI", "mongodb://localhost:27017"),
		MongoDB:  shared.Getenv("MONGO_DB", "cryptoscope"),

		ClickHouseAddr:     shared.Getenv("CLICKHOUSE_ADDR", "localhost:9000"),
		ClickHouseDB:       shared.Getenv("CLICKHOUSE_DB", "cryptoscope"),
		ClickHouseUser:     shared.Getenv("CLICKHOUSE_USER", "cryptoscope"),
		ClickHousePassword: shared.Getenv("CLICKHOUSE_PASSWORD", "cryptoscope"),

		Intervals: shared.GetenvList("PROCESSOR_INTERVALS", []string{"1m", "5m", "1h"}),
		TenantID:  shared.Getenv("TENANT_ID", "00000000-0000-0000-0000-000000000001"),

		OTLPEndpoint:  shared.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
		OTLPNamespace: shared.Getenv("OTEL_SERVICE_NAMESPACE", "cryptoscope"),
		MetricsAddr:   ":" + shared.Getenv("PROMETHEUS_METRICS_PORT", "9101"),
	}
}
