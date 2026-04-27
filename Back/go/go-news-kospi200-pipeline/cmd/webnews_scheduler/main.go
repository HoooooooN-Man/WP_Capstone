package main

import (
	"context"
	"log"
	"time"

	baseconfig "github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	webconfig "github.com/example/go-news-kospi200-pipeline/internal/webnews/config"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/redisstore"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/timewindow"
)

func main() {
	baseCfg := baseconfig.Load()

	webCfg, err := webconfig.LoadFromEnv()
	if err != nil {
		log.Fatalf("webnews_scheduler: load env failed: %v", err)
	}

	if err := webconfig.EnsureDataDirs(webCfg.DataDir); err != nil {
		log.Fatalf("webnews_scheduler: ensure data dirs failed: %v", err)
	}

	loc, err := webconfig.LoadLocation(webCfg.Timezone)
	if err != nil {
		log.Fatalf("webnews_scheduler: load timezone failed: %v", err)
	}

	categories, err := webconfig.LoadCategories(webCfg.CategoriesFile, webCfg.TopN)
	if err != nil {
		log.Fatalf("webnews_scheduler: load categories failed: %v", err)
	}

	client := redisx.NewClient(baseCfg)

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	if err := redisx.Ping(ctx, client); err != nil {
		log.Fatalf("webnews_scheduler: redis ping failed addr=%s err=%v", baseCfg.RedisAddr, err)
	}

	now := time.Now().In(loc)
	displayDate, windowStart, windowEnd := timewindow.Resolve(
		now,
		loc,
		webCfg.MarketOpenHour,
		webCfg.MarketOpenMinute,
	)

	log.Printf("webnews_scheduler: start now=%s display_date=%s window_start=%s window_end=%s redis=%s",
		now.Format(time.RFC3339),
		displayDate,
		windowStart.Format(time.RFC3339),
		windowEnd.Format(time.RFC3339),
		baseCfg.RedisAddr,
	)

	enqueued := 0
	for _, category := range categories {
		job := buildJob(displayDate, category, now, windowStart, windowEnd)
		msgID, err := redisstore.EnqueueCollectJob(ctx, client, webCfg.RedisPrefix, job)
		if err != nil {
			log.Fatalf("webnews_scheduler: enqueue failed category=%s err=%v", category.ID, err)
		}

		enqueued++
		log.Printf("webnews_scheduler: enqueued category=%s msg_id=%s query=%q mode=%s",
			category.ID, msgID, category.Query, category.Mode)
	}

	streamKey := redisstore.StreamCollectJobs(webCfg.RedisPrefix)
	xlen, err := client.XLen(ctx, streamKey).Result()
	if err != nil {
		log.Fatalf("webnews_scheduler: xlen failed stream=%s err=%v", streamKey, err)
	}

	log.Printf("webnews_scheduler: done enqueued=%d stream=%s xlen=%d", enqueued, streamKey, xlen)
}

func buildJob(displayDate string, category model.CategoryConfig, now, windowStart, windowEnd time.Time) model.CollectJob {
	return model.CollectJob{
		DisplayDate:   displayDate,
		CategoryID:    category.ID,
		CategoryLabel: category.Label,
		Mode:          category.Mode,
		Source:        category.Source,
		FeedURL:       category.FeedURL,
		Query:         category.Query,
		TopN:          category.TopN,
		ScheduledAt:   now.Format(time.RFC3339),
		WindowStart:   windowStart.Format(time.RFC3339),
		WindowEnd:     windowEnd.Format(time.RFC3339),
	}
}
