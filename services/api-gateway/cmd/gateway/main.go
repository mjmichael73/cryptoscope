package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/mojimich2015/cryptoscope/libs/go/logging"
	"github.com/mojimich2015/cryptoscope/libs/go/metrics"
	"github.com/mojimich2015/cryptoscope/libs/go/ratelimit"
	"github.com/mojimich2015/cryptoscope/libs/go/tracing"
	"github.com/mojimich2015/cryptoscope/services/api-gateway/internal/auth"
	"github.com/mojimich2015/cryptoscope/services/api-gateway/internal/client"
	"github.com/mojimich2015/cryptoscope/services/api-gateway/internal/config"
	"github.com/mojimich2015/cryptoscope/services/api-gateway/internal/gateway"
)

func main() {
	cfg := config.Load()
	logger := logging.New("api-gateway", cfg.LogLevel)
	environment := os.Getenv("APP_ENV")
	if environment == "" {
		environment = os.Getenv("ENVIRONMENT")
	}
	if err := cfg.Validate(environment); err != nil {
		logger.Error("invalid gateway configuration", "error", err)
		os.Exit(1)
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	shutdownTracing, err := tracing.Setup(ctx, tracing.Config{
		ServiceName:  "api-gateway",
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

	metricsServer := metrics.NewServer(cfg.MetricsPort)
	go func() {
		if err := metricsServer.Start(); err != nil {
			logger.Error("metrics server stopped", "error", err)
		}
	}()
	defer metricsServer.Close()

	redisClient := gateway.NewRedisClient(cfg.RedisAddr, cfg.RedisPassword, cfg.RedisDB)
	defer redisClient.Close()

	limiter := ratelimit.New(redisClient, cfg.RateLimitPerMinute, cfg.RateLimitBurst)

	keystore := auth.NewKeyStore(cfg.JWKSURL, cfg.Issuer, cfg.Audience)
	if !cfg.DevMode {
		if err := keystore.Refresh(ctx); err != nil {
			logger.Error("initial JWKS refresh failed", "error", err)
			os.Exit(1)
		}

		// Background JWKS refresh for key rotation
		go func() {
			ticker := time.NewTicker(15 * time.Minute)
			defer ticker.Stop()
			for {
				select {
				case <-ctx.Done():
					return
				case <-ticker.C:
					if err := keystore.Refresh(ctx); err != nil {
						logger.Warn("JWKS refresh failed", "error", err)
					} else {
						logger.Debug("JWKS keys refreshed")
					}
				}
			}
		}()
	}

	queryClient, err := client.NewQueryClient(cfg.GRPCAddr)
	if err != nil {
		logger.Error("query client connection failed", "error", err)
		os.Exit(1)
	}
	defer queryClient.Close()

	gw := gateway.New(queryClient, &cfg, logger, limiter, keystore)

	httpServer := &http.Server{
		Addr:         cfg.HTTPPort,
		Handler:      gw,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	go func() {
		logger.Info("api gateway starting", "port", cfg.HTTPPort)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("http server error", "error", err)
			os.Exit(1)
		}
	}()

	<-ctx.Done()
	logger.Info("shutting down api gateway")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		logger.Error("http server shutdown error", "error", err)
	}
	logger.Info("api gateway stopped cleanly")
}
