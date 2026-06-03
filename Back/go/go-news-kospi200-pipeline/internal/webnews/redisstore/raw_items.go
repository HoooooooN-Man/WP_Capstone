package redisstore

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
	"github.com/redis/go-redis/v9"
)

const EnrichGroupName = "enrich-group"

func EnsureRawGroup(ctx context.Context, client *redis.Client, prefix string) error {
	stream := StreamRawItems(prefix)

	err := client.XGroupCreateMkStream(ctx, stream, EnrichGroupName, "0").Err()
	if err != nil && !strings.Contains(err.Error(), "BUSYGROUP") {
		return fmt.Errorf("create enrich group: %w", err)
	}

	return nil
}

func ReadRawItems(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	consumer string,
	count int64,
	block time.Duration,
) ([]redis.XMessage, error) {
	pending, err := readRawItemsByID(ctx, client, prefix, consumer, count, 0, "0")
	if err != nil {
		return nil, err
	}
	if len(pending) > 0 {
		return pending, nil
	}

	return readRawItemsByID(ctx, client, prefix, consumer, count, block, ">")
}

func readRawItemsByID(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	consumer string,
	count int64,
	block time.Duration,
	streamID string,
) ([]redis.XMessage, error) {
	streams, err := client.XReadGroup(ctx, &redis.XReadGroupArgs{
		Group:    EnrichGroupName,
		Consumer: consumer,
		Streams:  []string{StreamRawItems(prefix), streamID},
		Count:    count,
		Block:    block,
	}).Result()

	if err == redis.Nil {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("read raw items: %w", err)
	}
	if len(streams) == 0 {
		return nil, nil
	}

	return streams[0].Messages, nil
}

func AckRawItem(ctx context.Context, client *redis.Client, prefix string, msgID string) error {
	if err := client.XAck(ctx, StreamRawItems(prefix), EnrichGroupName, msgID).Err(); err != nil {
		return fmt.Errorf("ack raw item: %w", err)
	}
	return nil
}

func EnqueueRawItem(ctx context.Context, client *redis.Client, prefix string, item model.RawNewsItem) (string, error) {
	return client.XAdd(ctx, &redis.XAddArgs{
		Stream: StreamRawItems(prefix),
		Values: map[string]any{
			"display_date":    item.DisplayDate,
			"category_id":     item.CategoryID,
			"category_label":  item.CategoryLabel,
			"rank":            strconv.Itoa(item.Rank),
			"title":           item.Title,
			"publisher":       item.Publisher,
			"google_news_url": item.GoogleNewsURL,
			"published_at":    item.PublishedAt,
			"collected_at":    item.CollectedAt,
			"source":          item.Source,
			"query":           item.Query,
			"raw_guid":        item.RawGUID,
		},
	}).Result()
}

func EnqueueRawItems(ctx context.Context, client *redis.Client, prefix string, items []model.RawNewsItem) error {
	for _, item := range items {
		if _, err := EnqueueRawItem(ctx, client, prefix, item); err != nil {
			return err
		}
	}
	return nil
}

func ParseRawItem(msg redis.XMessage) (model.RawNewsItem, error) {
	get := func(key string) string {
		if v, ok := msg.Values[key]; ok {
			return strings.TrimSpace(fmt.Sprint(v))
		}
		return ""
	}

	rank := 0
	if raw := get("rank"); raw != "" {
		v, err := strconv.Atoi(raw)
		if err != nil {
			return model.RawNewsItem{}, fmt.Errorf("invalid rank: %w", err)
		}
		rank = v
	}

	item := model.RawNewsItem{
		DisplayDate:   get("display_date"),
		CategoryID:    get("category_id"),
		CategoryLabel: get("category_label"),
		Rank:          rank,
		Title:         get("title"),
		Publisher:     get("publisher"),
		GoogleNewsURL: get("google_news_url"),
		PublishedAt:   get("published_at"),
		CollectedAt:   get("collected_at"),
		Source:        get("source"),
		Query:         get("query"),
		RawGUID:       get("raw_guid"),
	}

	if item.DisplayDate == "" || item.CategoryID == "" || item.Title == "" {
		return model.RawNewsItem{}, fmt.Errorf("missing required raw item fields msg_id=%s", msg.ID)
	}

	return item, nil
}
