package main

import (
	"context"
	"log"
	"os/signal"
	"syscall"

	"github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	"github.com/example/go-news-kospi200-pipeline/internal/rss"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	cfg := config.Load()
	client := redisx.NewClient(cfg)
	if err := redisx.Ping(ctx, client); err != nil {
		log.Fatal(err)
	}

	rssClient := rss.NewGoogleNewsClient()
	for _, query := range cfg.Queries {
		items, err := rssClient.Fetch(ctx, query)
		if err != nil {
			log.Printf("collector: query=%s err=%v", query, err)
			continue
		}
		for _, item := range items {
			if _, err := redisx.AddJSON(ctx, client, cfg.RawStream, item, 200000); err != nil {
				log.Printf("collector: push failed query=%s id=%s err=%v", query, item.NewsID, err)
				continue
			}
		}
		log.Printf("collector: query=%s fetched=%d", query, len(items))
	}
}
