package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"github.com/example/go-news-kospi200-pipeline/internal/aggregator"
	"github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	"github.com/example/go-news-kospi200-pipeline/internal/util"
)

func main() {
	util.SetupLogger("aggregator")

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	cfg := config.Load()
	client := redisx.NewClient(cfg)
	if err := redisx.Ping(ctx, client); err != nil {
		slog.Error("redis ping failed", "error", err.Error())
		os.Exit(1)
	}
	service := aggregator.NewService(cfg, client)
	slog.Info("aggregator started",
		"normalized_stream", cfg.NormalizedStream,
		"batch_ready_stream", cfg.BatchReadyStream,
	)
	if err := service.Run(ctx); err != nil && err != context.Canceled {
		slog.Error("aggregator service exited", "error", err.Error())
		os.Exit(1)
	}
}
