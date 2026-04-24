package main

import (
    "context"
    "log"
    "os/signal"
    "syscall"

    "github.com/example/go-news-kospi200-pipeline/internal/config"
    matcherpkg "github.com/example/go-news-kospi200-pipeline/internal/matcher"
    "github.com/example/go-news-kospi200-pipeline/internal/redisx"
)

func main() {
    ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
    defer stop()

    cfg := config.Load()
    client := redisx.NewClient(cfg)
    if err := redisx.Ping(ctx, client); err != nil {
        log.Fatal(err)
    }
    universe, err := matcherpkg.LoadUniverse(cfg.UniversePath)
    if err != nil {
        log.Fatal(err)
    }
    sourcePolicy := matcherpkg.LoadSourcePolicy(cfg.SourcePolicyPath)
    service := matcherpkg.NewService(cfg, client, universe, sourcePolicy)
    if err := service.Run(ctx); err != nil && err != context.Canceled {
        log.Fatal(err)
    }
}
