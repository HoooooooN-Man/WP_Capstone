package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	"github.com/example/go-news-kospi200-pipeline/internal/rss"
	"github.com/example/go-news-kospi200-pipeline/internal/util"
)

func main() {
	util.SetupLogger("collector")

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	cfg := config.Load()
	client := redisx.NewClient(cfg)
	if err := redisx.Ping(ctx, client); err != nil {
		slog.Error("redis ping failed", "error", err.Error())
		os.Exit(1)
	}

	rssClient := rss.NewGoogleNewsClient()
	for _, query := range cfg.Queries {
		items, err := rssClient.Fetch(ctx, query)
		if err != nil {
			slog.Warn("rss fetch failed", "query", query, "error", err.Error())
			continue
		}
		pushed := 0
		for _, item := range items {
			if _, err := redisx.AddJSON(ctx, client, cfg.RawStream, item, 200000); err != nil {
				slog.Warn("redis push failed",
					"query", query, "news_id", item.NewsID, "error", err.Error())
				continue
			}
			pushed++
		}
		slog.Info("query processed",
			"query", query, "fetched", len(items), "pushed", pushed)
	}
}
