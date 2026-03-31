package redisx

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
)

func EnsureGroup(ctx context.Context, client *redis.Client, stream, group string) error {
	err := client.XGroupCreateMkStream(ctx, stream, group, "0").Err()
	if err != nil && !strings.Contains(err.Error(), "BUSYGROUP") {
		return err
	}
	return nil
}

func AddJSON(ctx context.Context, client *redis.Client, stream string, payload any, maxLen int64) (string, error) {
	b, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}
	args := &redis.XAddArgs{
		Stream: stream,
		Values: map[string]any{"payload": string(b)},
	}
	if maxLen > 0 {
		args.MaxLen = maxLen
		args.Approx = true
	}
	return client.XAdd(ctx, args).Result()
}

func ReadGroup(ctx context.Context, client *redis.Client, group, consumer, stream string, block time.Duration, count int64) ([]redis.XMessage, error) {
	res, err := client.XReadGroup(ctx, &redis.XReadGroupArgs{
		Group:    group,
		Consumer: consumer,
		Streams:  []string{stream, ">"},
		Count:    count,
		Block:    block,
	}).Result()
	if err != nil {
		if errors.Is(err, redis.Nil) {
			return nil, nil
		}
		return nil, err
	}
	if len(res) == 0 {
		return nil, nil
	}
	return res[0].Messages, nil
}

func Ack(ctx context.Context, client *redis.Client, stream, group string, ids ...string) error {
	if len(ids) == 0 {
		return nil
	}
	return client.XAck(ctx, stream, group, ids...).Err()
}

func ParsePayload[T any](msg redis.XMessage) (T, error) {
	var zero T
	raw, ok := msg.Values["payload"]
	if !ok {
		return zero, fmt.Errorf("payload field not found in message %s", msg.ID)
	}
	var data []byte
	switch v := raw.(type) {
	case string:
		data = []byte(v)
	case []byte:
		data = v
	default:
		return zero, fmt.Errorf("unsupported payload type %T", raw)
	}
	var out T
	if err := json.Unmarshal(data, &out); err != nil {
		return zero, err
	}
	return out, nil
}
