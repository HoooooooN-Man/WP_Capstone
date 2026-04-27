package redisstore

import (
	"context"
	"fmt"
	"strconv"

	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
	"github.com/redis/go-redis/v9"
)

func UpsertEnrichedItem(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	item model.EnrichedNewsItem,
) (model.EnrichedNewsItem, error) {
	key := ItemKey(prefix, item.DisplayDate, item.ID)

	prevSeenCount := 0
	if v, err := client.HGet(ctx, key, "seen_count").Result(); err == nil {
		if n, convErr := strconv.Atoi(v); convErr == nil {
			prevSeenCount = n
		}
	}

	prevBestRank := 0
	if v, err := client.HGet(ctx, key, "best_rank").Result(); err == nil {
		if n, convErr := strconv.Atoi(v); convErr == nil {
			prevBestRank = n
		}
	}

	bestRank := item.BestRank
	if bestRank <= 0 {
		bestRank = item.LatestRank
	}
	if prevBestRank > 0 && (bestRank <= 0 || prevBestRank < bestRank) {
		bestRank = prevBestRank
	}

	item.SeenCount = prevSeenCount + 1
	item.BestRank = bestRank

	pipe := client.TxPipeline()

	pipe.HSetNX(ctx, key, "first_seen_at", item.FirstSeenAt)

	pipe.HSet(ctx, key, map[string]any{
		"id":             item.ID,
		"display_date":   item.DisplayDate,
		"category_id":    item.CategoryID,
		"category_label": item.CategoryLabel,

		"title":           item.Title,
		"publisher":       item.Publisher,
		"google_news_url": item.GoogleNewsURL,
		"origin_url":      item.OriginURL,
		"canonical_url":   item.CanonicalURL,
		"image_url":       item.ImageURL,

		"published_at": item.PublishedAt,
		"collected_at": item.CollectedAt,
		"last_seen_at": item.LastSeenAt,

		"source":   item.Source,
		"query":    item.Query,
		"raw_guid": item.RawGUID,

		"best_rank":   item.BestRank,
		"latest_rank": item.LatestRank,
		"seen_count":  item.SeenCount,
		"score":       fmt.Sprintf("%.4f", item.Score),
	})

	if _, err := pipe.Exec(ctx); err != nil {
		return model.EnrichedNewsItem{}, fmt.Errorf("upsert enriched item: %w", err)
	}

	return item, nil
}
