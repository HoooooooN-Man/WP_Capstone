package redisstore

import (
	"context"
	"fmt"
	"strconv"
	"strings"

	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
	"github.com/redis/go-redis/v9"
)

func TopRankedItemIDs(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	displayDate string,
	category string,
	limit int64,
) ([]string, error) {
	if limit <= 0 {
		limit = 10
	}

	key := RankKey(prefix, displayDate, category)
	ids, err := client.ZRevRange(ctx, key, 0, limit-1).Result()
	if err != nil {
		return nil, fmt.Errorf("zrevrange top ranked item ids: %w", err)
	}
	return ids, nil
}

func GetEnrichedItem(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	displayDate string,
	itemID string,
) (model.EnrichedNewsItem, error) {
	key := ItemKey(prefix, displayDate, itemID)

	values, err := client.HGetAll(ctx, key).Result()
	if err != nil {
		return model.EnrichedNewsItem{}, fmt.Errorf("hgetall enriched item: %w", err)
	}
	if len(values) == 0 {
		return model.EnrichedNewsItem{}, fmt.Errorf("item hash not found: %s", key)
	}

	parseInt := func(s string) int {
		n, _ := strconv.Atoi(strings.TrimSpace(s))
		return n
	}

	parseFloat := func(s string) float64 {
		f, _ := strconv.ParseFloat(strings.TrimSpace(s), 64)
		return f
	}

	item := model.EnrichedNewsItem{
		ID:            strings.TrimSpace(values["id"]),
		DisplayDate:   strings.TrimSpace(values["display_date"]),
		CategoryID:    strings.TrimSpace(values["category_id"]),
		CategoryLabel: strings.TrimSpace(values["category_label"]),

		Title:         strings.TrimSpace(values["title"]),
		Publisher:     strings.TrimSpace(values["publisher"]),
		GoogleNewsURL: strings.TrimSpace(values["google_news_url"]),
		OriginURL:     strings.TrimSpace(values["origin_url"]),
		CanonicalURL:  strings.TrimSpace(values["canonical_url"]),
		ImageURL:      strings.TrimSpace(values["image_url"]),

		PublishedAt: strings.TrimSpace(values["published_at"]),
		CollectedAt: strings.TrimSpace(values["collected_at"]),
		FirstSeenAt: strings.TrimSpace(values["first_seen_at"]),
		LastSeenAt:  strings.TrimSpace(values["last_seen_at"]),

		Source:  strings.TrimSpace(values["source"]),
		Query:   strings.TrimSpace(values["query"]),
		RawGUID: strings.TrimSpace(values["raw_guid"]),

		BestRank:   parseInt(values["best_rank"]),
		LatestRank: parseInt(values["latest_rank"]),
		SeenCount:  parseInt(values["seen_count"]),
		Score:      parseFloat(values["score"]),
	}

	if item.ID == "" {
		item.ID = itemID
	}
	if item.DisplayDate == "" {
		item.DisplayDate = displayDate
	}

	return item, nil
}
