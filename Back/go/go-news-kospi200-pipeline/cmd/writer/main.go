package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	"github.com/example/go-news-kospi200-pipeline/internal/util"
	writerpkg "github.com/example/go-news-kospi200-pipeline/internal/writer"
)

func main() {
	util.SetupLogger("writer")

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	cfg := config.Load()
	client := redisx.NewClient(cfg)
	if err := redisx.Ping(ctx, client); err != nil {
		slog.Error("redis ping failed", "error", err.Error())
		os.Exit(1)
	}

	// 기본 writer 는 파일 기반 spool writer.
	// DuckDB 담당자는 internal/writer/duckdb_stub.go 를 실제 구현으로 교체하면 됨.
	service := writerpkg.NewService(cfg, client, writerpkg.NewSpoolWriter(cfg.SpoolDir))
	slog.Info("writer started",
		"batch_ready_stream", cfg.BatchReadyStream,
		"spool_dir", cfg.SpoolDir,
	)
	if err := service.Run(ctx); err != nil && err != context.Canceled {
		slog.Error("writer service exited", "error", err.Error())
		os.Exit(1)
	}
}
