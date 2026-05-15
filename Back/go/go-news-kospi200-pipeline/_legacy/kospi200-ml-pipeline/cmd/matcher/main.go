package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"github.com/example/go-news-kospi200-pipeline/internal/config"
	matcherpkg "github.com/example/go-news-kospi200-pipeline/internal/matcher"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	"github.com/example/go-news-kospi200-pipeline/internal/util"
)

func main() {
	util.SetupLogger("matcher")

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	cfg := config.Load()
	client := redisx.NewClient(cfg)
	if err := redisx.Ping(ctx, client); err != nil {
		slog.Error("redis ping failed", "error", err.Error())
		os.Exit(1)
	}
	universe, err := matcherpkg.LoadUniverse(cfg.UniversePath)
	if err != nil {
		slog.Error("universe load failed", "path", cfg.UniversePath, "error", err.Error())
		os.Exit(1)
	}
	sourcePolicy := matcherpkg.LoadSourcePolicy(cfg.SourcePolicyPath)
	service := matcherpkg.NewService(cfg, client, universe, sourcePolicy)
	slog.Info("matcher started",
		"universe_size", len(universe.Companies),
		"raw_stream", cfg.RawStream,
		"normalized_stream", cfg.NormalizedStream,
	)
	if err := service.Run(ctx); err != nil && err != context.Canceled {
		slog.Error("matcher service exited", "error", err.Error())
		os.Exit(1)
	}
}
