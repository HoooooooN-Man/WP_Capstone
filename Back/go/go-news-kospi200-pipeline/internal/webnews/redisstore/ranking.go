package redisstore

import (
	"context"
	"fmt"

	"github.com/redis/go-redis/v9"
)

func ScoreDelta(rank int) float64 {
	switch rank {
	case 1:
		return 10.0
	case 2:
		return 9.0
	case 3:
		return 8.0
	case 4:
		return 7.0
	case 5:
		return 6.0
	case 6:
		return 5.0
	case 7:
		return 4.0
	case 8:
		return 3.0
	case 9:
		return 2.0
	case 10:
		return 1.0
	default:
		return 0.5
	}
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
