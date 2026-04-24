package redisx

import (
	"context"
	"time"

	"github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/redis/go-redis/v9"
)

func NewClient(cfg config.Config) *redis.Client {
	return redis.NewClient(&redis.Options{
		Addr:         cfg.RedisAddr,
		Password:     cfg.RedisPassword,
		DB:           cfg.RedisDB,
		Protocol:     cfg.RedisProtocol,
		DialTimeout:  5 * time.Second,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
		PoolSize:     10,
		MaxRetries:   3,
	})
}

func Ping(ctx context.Context, client *redis.Client) error {
	return client.Ping(ctx).Err()
}
