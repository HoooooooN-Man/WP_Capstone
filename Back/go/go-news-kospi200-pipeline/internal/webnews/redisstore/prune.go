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
func DeleteDateScopedKeys(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	displayDate string,
) (int, error) {
	patterns := []string{
		fmt.Sprintf("%s:%s:rank:*", prefix, displayDate),
		fmt.Sprintf("%s:%s:item:*", prefix, displayDate),
		fmt.Sprintf("%s:%s:seen:*", prefix, displayDate),
		fmt.Sprintf("%s:%s:lock:*", prefix, displayDate),
	}

	totalDeleted := 0

	for _, pattern := range patterns {
		deleted, err := unlinkMatchingKeysForDatePrune(ctx, client, pattern)
		if err != nil {
			return totalDeleted, err
		}
		totalDeleted += deleted
	}

	return totalDeleted, nil
}

func unlinkMatchingKeysForDatePrune(
	ctx context.Context,
	client *redis.Client,
	pattern string,
) (int, error) {
	var cursor uint64
	totalDeleted := 0

	for {
		keys, nextCursor, err := client.Scan(ctx, cursor, pattern, 200).Result()
		if err != nil {
			return totalDeleted, fmt.Errorf("scan keys pattern=%s: %w", pattern, err)
		}

		if len(keys) > 0 {
			deleted, err := client.Unlink(ctx, keys...).Result()
			if err != nil {
				return totalDeleted, fmt.Errorf("unlink keys pattern=%s: %w", pattern, err)
			}
			totalDeleted += int(deleted)
		}

		cursor = nextCursor
		if cursor == 0 {
			break
		}
	}

	return totalDeleted, nil
}
