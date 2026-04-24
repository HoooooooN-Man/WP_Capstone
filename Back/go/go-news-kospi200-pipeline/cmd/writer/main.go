package main

import (
	"context"
	"log"
	"os/signal"
	"syscall"

	"github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	writerpkg "github.com/example/go-news-kospi200-pipeline/internal/writer"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	cfg := config.Load()
	client := redisx.NewClient(cfg)
	if err := redisx.Ping(ctx, client); err != nil {
		log.Fatal(err)
	}

	// Default writer is a file-based spool writer.
	// The DuckDB 담당자는 internal/writer/duckdb_stub.go를 실제 구현으로 교체하면 됨.
	service := writerpkg.NewService(cfg, client, writerpkg.NewSpoolWriter(cfg.SpoolDir))
	if err := service.Run(ctx); err != nil && err != context.Canceled {
		log.Fatal(err)
	}
}
