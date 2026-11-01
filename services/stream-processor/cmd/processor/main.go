// Command processor runs the stream processing service. It consumes raw ticks
// from Kafka, archives them, folds them into candles, and persists the closed
// candles to ClickHouse for the analytics read side.
package main

import (
	"context"
	"errors"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/mojimich2015/cryptoscope/libs/go/kafka"
	"github.com/mojimich2015/cryptoscope/libs/go/logging"
	"github.com/mojimich2015/cryptoscope/libs/go/metrics"
	"github.com/mojimich2015/cryptoscope/libs/go/tracing"
	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/aggregate"
	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/config"
	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/etl"
	"github.com/mojimich2015/cryptoscope/services/stream-processor/internal/store"
)

func main() {
	cfg := config.Load()
	logger := logging.New("stream-processor", cfg.LogLevel)
	kafkaConfig, err := kafka.LoadClientConfig()
	if err != nil {
		logger.Error("invalid Kafka configuration", "error", err)
		os.Exit(1)
	}
	kafkaTransport, err := kafkaConfig.Transport()
	if err != nil {
		logger.Error("invalid Kafka transport configuration", "error", err)
		os.Exit(1)
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	shutdownTracing, err := tracing.Setup(ctx, tracing.Config{
		ServiceName:  "stream-processor",
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

	archive, err := store.NewMongoArchive(ctx, cfg.MongoURI, cfg.MongoDB)
	if err != nil {
		logger.Error("mongo connect failed", "error", err)
		os.Exit(1)
	}

	candles, err := store.NewClickHouseCandles(ctx, cfg.ClickHouseAddr, cfg.ClickHouseDB, cfg.ClickHouseUser, cfg.ClickHousePassword)
	if err != nil {
		logger.Error("clickhouse connect failed", "error", err)
		os.Exit(1)
	}

	aggregator := aggregate.New(cfg.Intervals)
	producer := kafka.NewProducerWithTransport(cfg.KafkaBrokers, cfg.EventsTopic, kafkaTransport)
	defer producer.Close()

	proc := etl.New(aggregator, archive, candles, producer, cfg.EventsTopic, cfg.TenantID, logger)

	consumer := kafka.NewConsumerWithTransport(cfg.KafkaBrokers, cfg.TicksTopic, cfg.ConsumerGroup, kafkaTransport)
	defer consumer.Close()

	logger.Info("stream processor starting",
		"topic", cfg.TicksTopic,
		"group", cfg.ConsumerGroup,
		"intervals", cfg.Intervals,
	)

	if err := run(ctx, consumer, proc, logger); err != nil && !errors.Is(err, context.Canceled) {
		logger.Error("processor stopped with error", "error", err)
		os.Exit(1)
	}

	flushCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := proc.Flush(flushCtx); err != nil {
		logger.Error("flush on shutdown failed", "error", err)
	}
	logger.Info("stream processor stopped cleanly")
}

func run(ctx context.Context, consumer *kafka.Consumer, proc *etl.Processor, logger *slog.Logger) error {
	for {
		msg, err := consumer.Fetch(ctx)
		if err != nil {
			return err
		}
		if err := proc.Handle(ctx, msg.Value); err != nil {
			// Do not commit the offset so the message is retried on redelivery.
			logger.Error("handling tick failed, will retry", "error", err)
			continue
		}
		if err := consumer.Commit(ctx, msg); err != nil {
			logger.Error("commit failed", "error", err)
		}
	}
}
