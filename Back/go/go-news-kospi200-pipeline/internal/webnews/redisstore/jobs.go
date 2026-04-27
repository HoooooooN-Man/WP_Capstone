package redisstore

import (
	"context"
	"strconv"

	"github.com/example/go-news-kospi200-pipeline/internal/webnews/model"
	"github.com/redis/go-redis/v9"
)

func EnqueueCollectJob(ctx context.Context, client *redis.Client, prefix string, job model.CollectJob) (string, error) {
	return client.XAdd(ctx, &redis.XAddArgs{
		Stream: StreamCollectJobs(prefix),
		Values: map[string]any{
			"display_date":   job.DisplayDate,
			"category_id":    job.CategoryID,
			"category_label": job.CategoryLabel,
			"mode":           job.Mode,
			"source":         job.Source,
			"feed_url":       job.FeedURL,
			"query":          job.Query,
			"top_n":          strconv.Itoa(job.TopN),
			"scheduled_at":   job.ScheduledAt,
			"window_start":   job.WindowStart,
			"window_end":     job.WindowEnd,
		},
	}).Result()
}
