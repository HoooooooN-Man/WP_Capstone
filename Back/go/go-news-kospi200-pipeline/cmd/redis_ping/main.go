package main

import (
	"context"
	"log"
	"os/signal"
	"syscall"
	"time"

	"github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	cfg := config.Load()
	client := redisx.NewClient(cfg)

	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	started := time.Now()
	if err := redisx.Ping(pingCtx, client); err != nil {
		log.Fatalf("redis_ping: FAIL addr=%s err=%v", cfg.RedisAddr, err)
	}

	log.Printf("redis_ping: OK addr=%s latency=%s raw_stream=%s normalized_stream=%s batch_stream=%s",
		cfg.RedisAddr,
		time.Since(started).Round(time.Millisecond),
		cfg.RawStream,
		cfg.NormalizedStream,
		cfg.BatchReadyStream,
	)
}
