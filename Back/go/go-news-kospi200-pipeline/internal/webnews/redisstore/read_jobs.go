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

const CollectGroupName = "collect-group"

func EnsureCollectGroup(ctx context.Context, client *redis.Client, prefix string) error {
	stream := StreamCollectJobs(prefix)

	err := client.XGroupCreateMkStream(ctx, stream, CollectGroupName, "0").Err()
	if err != nil && !strings.Contains(err.Error(), "BUSYGROUP") {
		return fmt.Errorf("create collect group: %w", err)
	}

	return nil
}

func ReadCollectJobs(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	consumer string,
	count int64,
	block time.Duration,
) ([]redis.XMessage, error) {
	// 1) 먼저 현재 consumer에 pending 된 메시지가 있으면 재처리
	pending, err := readCollectJobsByID(ctx, client, prefix, consumer, count, 0, "0")
	if err != nil {
		return nil, err
	}
	if len(pending) > 0 {
		return pending, nil
	}

	// 2) 없으면 새 메시지 대기
	return readCollectJobsByID(ctx, client, prefix, consumer, count, block, ">")
}

func readCollectJobsByID(
	ctx context.Context,
	client *redis.Client,
	prefix string,
	consumer string,
	count int64,
	block time.Duration,
	streamID string,
) ([]redis.XMessage, error) {
	streams, err := client.XReadGroup(ctx, &redis.XReadGroupArgs{
		Group:    CollectGroupName,
		Consumer: consumer,
		Streams:  []string{StreamCollectJobs(prefix), streamID},
		Count:    count,
		Block:    block,
	}).Result()

	if err == redis.Nil {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("read collect jobs: %w", err)
	}
	if len(streams) == 0 {
		return nil, nil
	}

	return streams[0].Messages, nil
}

func ParseCollectJob(msg redis.XMessage) (model.CollectJob, error) {
	get := func(key string) string {
		if v, ok := msg.Values[key]; ok {
			return strings.TrimSpace(fmt.Sprint(v))
		}
		return ""
	}

	topN := 10
	if raw := get("top_n"); raw != "" {
		v, err := strconv.Atoi(raw)
		if err != nil {
			return model.CollectJob{}, fmt.Errorf("invalid top_n: %w", err)
		}
		topN = v
	}

	job := model.CollectJob{
		DisplayDate:   get("display_date"),
		CategoryID:    get("category_id"),
		CategoryLabel: get("category_label"),
		Mode:          get("mode"),
		Source:        get("source"),
		FeedURL:       get("feed_url"),
		Query:         get("query"),
		TopN:          topN,
		ScheduledAt:   get("scheduled_at"),
		WindowStart:   get("window_start"),
		WindowEnd:     get("window_end"),
	}

	if job.DisplayDate == "" || job.CategoryID == "" {
		return model.CollectJob{}, fmt.Errorf("missing required job fields msg_id=%s", msg.ID)
	}
	if job.CategoryLabel == "" {
		job.CategoryLabel = job.CategoryID
	}
	if job.Mode == "" {
		job.Mode = "search"
	}
	if job.Source == "" {
		job.Source = "google_news"
	}

	return job, nil
}

func AckCollectJob(ctx context.Context, client *redis.Client, prefix string, msgID string) error {
	if err := client.XAck(ctx, StreamCollectJobs(prefix), CollectGroupName, msgID).Err(); err != nil {
		return fmt.Errorf("ack collect job: %w", err)
	}
	return nil
}
