package redisstore

import (
	"context"
	"fmt"

	"github.com/redis/go-redis/v9"
)

func DeleteTransientStreams(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	includePublishEvents bool,
) (int, error) {
	keys := []string{
		StreamCollectJobs(prefix),
		StreamRawItems(prefix),
	}

	if includePublishEvents {
		keys = append(keys, StreamPublishEvents(prefix))
	}

	deleted, err := client.Unlink(ctx, keys...).Result()
	if err != nil {
		return 0, fmt.Errorf("unlink transient streams: %w", err)
	}

	return int(deleted), nil
}

func TrimPublishEvents(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	maxLen int64,
) (int64, error) {
	key := StreamPublishEvents(prefix)

	if maxLen <= 0 {
		if err := client.Unlink(ctx, key).Err(); err != nil {
			return 0, fmt.Errorf("unlink publish events: %w", err)
		}
		return 0, nil
	}

	if err := client.XTrimMaxLen(ctx, key, maxLen).Err(); err != nil {
		return 0, fmt.Errorf("xtrim publish events: %w", err)
	}

	length, err := client.XLen(ctx, key).Result()
	if err != nil {
		return 0, fmt.Errorf("xlen publish events: %w", err)
	}

	return length, nil
}
