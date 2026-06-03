package redisstore

import (
	"context"
	"encoding/json"
	"fmt"
	"path/filepath"

	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
	"github.com/redis/go-redis/v9"
)

func CurrentManifestKey(prefix string) string {
	return fmt.Sprintf("%s:current:manifest", prefix)
}

func SetCurrentManifest(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	manifest model.FinalizeManifest,
	currentDir string,
) error {
	raw, err := json.Marshal(manifest)
	if err != nil {
		return fmt.Errorf("marshal manifest: %w", err)
	}

	if err := client.HSet(ctx, CurrentManifestKey(prefix), map[string]any{
		"display_date":  manifest.DisplayDate,
		"window_start":  manifest.WindowStart,
		"window_end":    manifest.WindowEnd,
		"generated_at":  manifest.GeneratedAt,
		"top_n":         manifest.TopN,
		"current_dir":   filepath.Clean(currentDir),
		"manifest_json": string(raw),
	}).Err(); err != nil {
		return fmt.Errorf("hset current manifest: %w", err)
	}

	return nil
}

func AddPublishEvent(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	displayDate string,
	currentDir string,
) error {
	if err := client.XAdd(ctx, &redis.XAddArgs{
		Stream: StreamPublishEvents(prefix),
		Values: map[string]any{
			"display_date": displayDate,
			"current_dir":  filepath.Clean(currentDir),
		},
	}).Err(); err != nil {
		return fmt.Errorf("xadd publish event: %w", err)
	}

	return nil
}

func DeleteDateScopedKeysExcept(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	keepDisplayDate string,
) (int, error) {
	patterns := []string{
		fmt.Sprintf("%s:*:item:*", prefix),
		fmt.Sprintf("%s:*:rank:*", prefix),
		fmt.Sprintf("%s:*:seen:*", prefix),
		fmt.Sprintf("%s:*:lock:*", prefix),
	}

	totalDeleted := 0

	for _, pattern := range patterns {
		deleted, err := deleteByPatternExceptDate(ctx, client, pattern, prefix, keepDisplayDate)
		if err != nil {
			return totalDeleted, err
		}
		totalDeleted += deleted
	}

	return totalDeleted, nil
}

func deleteByPatternExceptDate(
	ctx context.Context,
	client *redis.Client,
	pattern string,
	prefix string,
	keepDisplayDate string,
) (int, error) {
	var cursor uint64
	totalDeleted := 0

	for {
		keys, nextCursor, err := client.Scan(ctx, cursor, pattern, 200).Result()
		if err != nil {
			return totalDeleted, fmt.Errorf("scan keys pattern=%s: %w", pattern, err)
		}

		toDelete := make([]string, 0, len(keys))
		for _, key := range keys {
			datePart := extractDisplayDateFromKey(prefix, key)
			if datePart == "" {
				continue
			}
			if datePart == keepDisplayDate {
				continue
			}
			toDelete = append(toDelete, key)
		}

		if len(toDelete) > 0 {
			n, err := client.Unlink(ctx, toDelete...).Result()
			if err != nil {
				return totalDeleted, fmt.Errorf("unlink keys: %w", err)
			}
			totalDeleted += int(n)
		}

		cursor = nextCursor
		if cursor == 0 {
			break
		}
	}

	return totalDeleted, nil
}

func extractDisplayDateFromKey(prefix string, key string) string {
	// 예: webnews:2026-04-22:item:abcd
	//     webnews:2026-04-22:rank:business
	wantPrefix := prefix + ":"
	if len(key) <= len(wantPrefix) || key[:len(wantPrefix)] != wantPrefix {
		return ""
	}

	rest := key[len(wantPrefix):]
	for i := 0; i < len(rest); i++ {
		if rest[i] == ':' {
			return rest[:i]
		}
	}
	return ""
}
