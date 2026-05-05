package main

import (
	"context"
	"crypto/sha1"
	"encoding/hex"
	"errors"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	baseconfig "github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/config"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
	"github.com/example/go-news-kospi200-pipeline/internal/webnews/redisstore"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	baseCfg := baseconfig.Load()

	webCfg, err := config.LoadFromEnv()
	if err != nil {
		log.Fatalf("webnews_enricher: load env failed: %v", err)
	}

	client := redisx.NewClient(baseCfg)

	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	if err := redisx.Ping(pingCtx, client); err != nil {
		cancel()
		log.Fatalf("webnews_enricher: redis ping failed addr=%s err=%v", baseCfg.RedisAddr, err)
	}
	cancel()

	if err := redisstore.EnsureRawGroup(ctx, client, webCfg.RedisPrefix); err != nil {
		log.Fatalf("webnews_enricher: ensure raw group failed: %v", err)
	}

	consumerName := hostnameOr("webnews-enricher-1")

	log.Printf(
		"webnews_enricher: start redis=%s stream=%s consumer=%s",
		baseCfg.RedisAddr,
		redisstore.StreamRawItems(webCfg.RedisPrefix),
		consumerName,
	)

	for {
		select {
		case <-ctx.Done():
			log.Printf("webnews_enricher: shutdown requested")
			return
		default:
		}

		messages, err := redisstore.ReadRawItems(
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
			log.Printf("webnews_enricher: read raw items error: %v", err)
			time.Sleep(2 * time.Second)
			continue
		}

		if len(messages) == 0 {
			continue
		}

		for _, msg := range messages {
			rawItem, err := redisstore.ParseRawItem(msg)
			if err != nil {
				log.Printf("webnews_enricher: parse raw item failed msg_id=%s err=%v", msg.ID, err)
				_ = redisstore.AckRawItem(ctx, client, webCfg.RedisPrefix, msg.ID)
				continue
			}

			enrichedItem := enrichOne(rawItem)

			scoreDelta := redisstore.ScoreDelta(enrichedItem.LatestRank)

			score, err := redisstore.AddRankScore(
				ctx,
				client,
				webCfg.RedisPrefix,
				enrichedItem.DisplayDate,
				enrichedItem.CategoryID,
				enrichedItem.ID,
				scoreDelta,
			)
			if err != nil {
				log.Printf("webnews_enricher: add rank score failed msg_id=%s item_id=%s err=%v", msg.ID, enrichedItem.ID, err)
				continue
			}
			enrichedItem.Score = score

			storedItem, err := redisstore.UpsertEnrichedItem(ctx, client, webCfg.RedisPrefix, enrichedItem)
			if err != nil {
				log.Printf("webnews_enricher: upsert enriched item failed msg_id=%s item_id=%s err=%v", msg.ID, enrichedItem.ID, err)
				continue
			}

			if err := redisstore.AckRawItem(ctx, client, webCfg.RedisPrefix, msg.ID); err != nil {
				log.Printf("webnews_enricher: ack raw item failed msg_id=%s err=%v", msg.ID, err)
				continue
			}

			log.Printf(
				"webnews_enricher: stored msg_id=%s category=%s item_id=%s seen=%d score=%.2f rss_only=true",
				msg.ID,
				storedItem.CategoryID,
				storedItem.ID,
				storedItem.SeenCount,
				storedItem.Score,
			)
		}
	}
}

func enrichOne(raw model.RawNewsItem) model.EnrichedNewsItem {
	now := time.Now().Format(time.RFC3339)

	itemID := buildSimpleItemID(raw.Title, raw.Publisher, raw.GoogleNewsURL)

	return model.EnrichedNewsItem{
		ID:            itemID,
		DisplayDate:   raw.DisplayDate,
		CategoryID:    raw.CategoryID,
		CategoryLabel: raw.CategoryLabel,

		Title:         strings.TrimSpace(raw.Title),
		Publisher:     strings.TrimSpace(raw.Publisher),
		GoogleNewsURL: strings.TrimSpace(raw.GoogleNewsURL),

		PublishedAt: strings.TrimSpace(raw.PublishedAt),
		CollectedAt: strings.TrimSpace(raw.CollectedAt),
		FirstSeenAt: now,
		LastSeenAt:  now,

		Source:  strings.TrimSpace(raw.Source),
		Query:   strings.TrimSpace(raw.Query),
		RawGUID: strings.TrimSpace(raw.RawGUID),

		BestRank:   raw.Rank,
		LatestRank: raw.Rank,
		SeenCount:  1,
	}
}

func buildSimpleItemID(title, publisher, googleNewsURL string) string {
	key := normalizeForID(title) + "|" + normalizeForID(publisher) + "|" + strings.TrimSpace(googleNewsURL)
	sum := sha1.Sum([]byte(key))
	return hex.EncodeToString(sum[:])
}

func normalizeForID(s string) string {
	s = strings.TrimSpace(strings.ToLower(s))
	s = strings.NewReplacer(
		"ㆍ", " ",
		"·", " ",
		"•", " ",
		"\t", " ",
		"\n", " ",
		"\r", " ",
	).Replace(s)
	s = strings.Join(strings.Fields(s), " ")
	return s
}

func hostnameOr(fallback string) string {
	name, err := os.Hostname()
	if err != nil || name == "" {
		return fallback
	}
	return name
}
