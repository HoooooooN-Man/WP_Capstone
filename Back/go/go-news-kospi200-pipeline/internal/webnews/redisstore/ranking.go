package redisstore

import (
	"context"
	"fmt"
	"strings"

	"github.com/redis/go-redis/v9"
)

func ScoreDelta(rank int, imageURL, originURL, googleNewsURL string) float64 {
	base := 1.0
	if rank > 0 && rank <= 10 {
		base = float64(11 - rank)
	}

	if strings.TrimSpace(imageURL) != "" {
		base += 0.2
	}
	if strings.TrimSpace(originURL) != "" && strings.TrimSpace(originURL) != strings.TrimSpace(googleNewsURL) {
		base += 0.2
	}

	return base
}

func AddRankScore(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	displayDate string,
	category string,
	itemID string,
	delta float64,
) (float64, error) {
	key := RankKey(prefix, displayDate, category)

	if err := client.ZIncrBy(ctx, key, delta, itemID).Err(); err != nil {
		return 0, fmt.Errorf("zincrby rank score: %w", err)
	}

	score, err := client.ZScore(ctx, key, itemID).Result()
	if err != nil {
		return 0, fmt.Errorf("zscore rank score: %w", err)
	}

	return score, nil
}
