package main

import (
	"context"
	"errors"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	baseconfig "github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/collector"
	webconfig "github.com/example/go-news-kospi200-pipeline/internal/webnews/config"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/redisstore"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	baseCfg := baseconfig.Load()

	webCfg, err := webconfig.LoadFromEnv()
	if err != nil {
		log.Fatalf("webnews_collector: load env failed: %v", err)
	}

	client := redisx.NewClient(baseCfg)

	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	if err := redisx.Ping(pingCtx, client); err != nil {
		cancel()
		log.Fatalf("webnews_collector: redis ping failed addr=%s err=%v", baseCfg.RedisAddr, err)
	}
	cancel()

	consumerName := hostnameOr("webnews-collector-1")

	if err := redisstore.EnsureCollectGroup(ctx, client, webCfg.RedisPrefix); err != nil {
		log.Fatalf("webnews_collector: ensure group failed: %v", err)
	}

	rssClient := collector.NewGoogleRSSClient(webCfg.FetchTimeout, webCfg.UserAgent)

	log.Printf(
		"webnews_collector: start redis=%s stream=%s consumer=%s",
		baseCfg.RedisAddr,
		redisstore.StreamCollectJobs(webCfg.RedisPrefix),
		consumerName,
	)

	for {
		select {
		case <-ctx.Done():
			log.Printf("webnews_collector: shutdown requested")
			return
		default:
		}

		messages, err := redisstore.ReadCollectJobs(
			ctx,
			client,
			webCfg.RedisPrefix,
			consumerName,
			10,
			baseCfg.PollBlock,
		)
		if err != nil {
			if errors.Is(err, context.Canceled) {
				return
			}
			log.Printf("webnews_collector: read jobs error: %v", err)
			time.Sleep(2 * time.Second)
			continue
		}

		if len(messages) == 0 {
			continue
		}

		for _, msg := range messages {
			job, err := redisstore.ParseCollectJob(msg)
			if err != nil {
				log.Printf("webnews_collector: parse job failed msg_id=%s err=%v", msg.ID, err)
				_ = redisstore.AckCollectJob(ctx, client, webCfg.RedisPrefix, msg.ID)
				continue
			}

			items, err := rssClient.FetchByJob(ctx, job)
			if err != nil {
				log.Printf(
					"webnews_collector: fetch failed msg_id=%s category=%s err=%v",
					msg.ID,
					job.CategoryID,
					err,
				)
				// ack 하지 않음 -> 같은 consumer가 다음 루프에서 pending 재시도
				continue
			}

			if len(items) == 0 {
				log.Printf("webnews_collector: no items msg_id=%s category=%s", msg.ID, job.CategoryID)
				if err := redisstore.AckCollectJob(ctx, client, webCfg.RedisPrefix, msg.ID); err != nil {
					log.Printf("webnews_collector: ack empty job failed msg_id=%s err=%v", msg.ID, err)
				}
				continue
			}

			if err := redisstore.EnqueueRawItems(ctx, client, webCfg.RedisPrefix, items); err != nil {
				log.Printf(
					"webnews_collector: enqueue raw items failed msg_id=%s category=%s err=%v",
					msg.ID,
					job.CategoryID,
					err,
				)
				continue
			}

			if err := redisstore.AckCollectJob(ctx, client, webCfg.RedisPrefix, msg.ID); err != nil {
				log.Printf("webnews_collector: ack failed msg_id=%s err=%v", msg.ID, err)
				continue
			}

			log.Printf(
				"webnews_collector: collected msg_id=%s category=%s items=%d query=%q",
				msg.ID,
				job.CategoryID,
				len(items),
				job.Query,
			)
		}
	}
}

func hostnameOr(fallback string) string {
	name, err := os.Hostname()
	if err != nil || name == "" {
		return fallback
	}
	return name
}
