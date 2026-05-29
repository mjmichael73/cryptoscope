// Command ingest runs the market data ingestion service. It polls the public
// market data sources on a schedule, drops duplicates, and publishes normalized
// ticks to Kafka.
package main

import (
	"context"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/redis/go-redis/v9"

	"github.com/mojimich2015/cryptoscope/libs/go/idempotency"
	"github.com/mojimich2015/cryptoscope/libs/go/kafka"
	"github.com/mojimich2015/cryptoscope/libs/go/logging"
	"github.com/mojimich2015/cryptoscope/libs/go/metrics"
	"github.com/mojimich2015/cryptoscope/libs/go/tracing"
	"github.com/mojimich2015/cryptoscope/services/ingest-service/internal/config"
	"github.com/mojimich2015/cryptoscope/services/ingest-service/internal/pipeline"
	"github.com/mojimich2015/cryptoscope/services/ingest-service/internal/source"
)

func main() {
	cfg := config.Load()
	logger := logging.New("ingest-service", cfg.LogLevel)

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	shutdownTracing, err := tracing.Setup(ctx, tracing.Config{
		ServiceName:  "ingest-service",
		Namespace:    cfg.OTLPNamespace,
		OTLPEndpoint: cfg.OTLPEndpoint,
	})
	if err != nil {
		logger.Warn("tracing setup failed, continuing without traces", "error", err)
	} else {
		defer func() {
			shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			_ = shutdownTracing(shutdownCtx)
		}()
	}

	metricsServer := metrics.NewServer(cfg.MetricsAddr)
	go func() {
		if err := metricsServer.Start(); err != nil {
			logger.Error("metrics server stopped", "error", err)
		}
	}()
	defer metricsServer.Close()

	redisClient := redis.NewClient(&redis.Options{
		Addr:     cfg.RedisAddr,
		Password: cfg.RedisPassword,
		DB:       cfg.RedisDB,
	})
	defer redisClient.Close()

	deduper := idempotency.NewStore(redisClient, "ingest:dedupe", 24*time.Hour)

	producer := kafka.NewProducer(cfg.KafkaBrokers, cfg.TicksTopic)
	defer producer.Close()

	proc := pipeline.New(deduper, producer, logger)

	sources := []source.Source{
		source.NewBinance(cfg.BinanceBaseURL),
		source.NewCoinbase(cfg.CoinbaseBaseURL),
	}

	scheduler := pipeline.NewScheduler(sources, cfg.Symbols, cfg.PollInterval, proc, logger)

	logger.Info("ingest service starting",
		"symbols", cfg.Symbols,
		"interval", cfg.PollInterval.String(),
		"topic", cfg.TicksTopic,
	)

	if err := scheduler.Run(ctx); err != nil && err != context.Canceled {
		logger.Error("scheduler stopped with error", "error", err)
		os.Exit(1)
	}
	logger.Info("ingest service stopped cleanly")
}
