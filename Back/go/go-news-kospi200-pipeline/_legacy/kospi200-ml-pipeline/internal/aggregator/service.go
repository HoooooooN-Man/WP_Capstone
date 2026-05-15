package aggregator

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/example/go-news-kospi200-pipeline/internal/config"
	"github.com/example/go-news-kospi200-pipeline/internal/model"
	"github.com/example/go-news-kospi200-pipeline/internal/redisx"
	"github.com/redis/go-redis/v9"
)

type Service struct {
	cfg    config.Config
	client *redis.Client
	buf    []model.NormalizedNewsEvent
	first  time.Time
}

func NewService(cfg config.Config, client *redis.Client) *Service {
	return &Service{cfg: cfg, client: client, buf: make([]model.NormalizedNewsEvent, 0, cfg.BatchMaxItems)}
}

func (s *Service) Run(ctx context.Context) error {
	if err := redisx.EnsureGroup(ctx, s.client, s.cfg.NormalizedStream, s.cfg.NormalizedGroup); err != nil {
		return err
	}
	ticker := time.NewTicker(s.cfg.BatchFlushInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return s.flush(ctx)
		case <-ticker.C:
			if err := s.flush(ctx); err != nil {
				return err
			}
		default:
		}

		msgs, err := redisx.ReadGroup(ctx, s.client, s.cfg.NormalizedGroup, s.cfg.NormalizedConsumer, s.cfg.NormalizedStream, s.cfg.PollBlock, 50)
		if err != nil {
			return err
		}
		if len(msgs) == 0 {
			continue
		}
		for _, msg := range msgs {
			item, err := redisx.ParsePayload[model.NormalizedNewsEvent](msg)
			if err != nil {
				log.Printf("aggregator: parse error: %v", err)
				_ = redisx.Ack(ctx, s.client, s.cfg.NormalizedStream, s.cfg.NormalizedGroup, msg.ID)
				continue
			}
			if err := s.indexForRealtime(ctx, item); err != nil {
				return err
			}
			if len(s.buf) == 0 {
				s.first = time.Now()
			}
			s.buf = append(s.buf, item)
			if err := redisx.Ack(ctx, s.client, s.cfg.NormalizedStream, s.cfg.NormalizedGroup, msg.ID); err != nil {
				return err
			}
			if len(s.buf) >= s.cfg.BatchMaxItems {
				if err := s.flush(ctx); err != nil {
					return err
				}
			}
		}
	}
}

func (s *Service) indexForRealtime(ctx context.Context, item model.NormalizedNewsEvent) error {
	score := float64(item.PublishedAt.Unix())
	marketKey := "news:agg:market:recent"
	if err := s.client.ZAdd(ctx, marketKey, redis.Z{Score: score, Member: item.NewsID}).Err(); err != nil {
		return err
	}
	_ = s.client.Expire(ctx, marketKey, s.cfg.FrontWindowDuration).Err()
	for _, m := range item.Matched {
		key := fmt.Sprintf("news:agg:company:%s:recent", m.Ticker)
		if err := s.client.ZAdd(ctx, key, redis.Z{Score: score, Member: item.NewsID}).Err(); err != nil {
			return err
		}
		_ = s.client.Expire(ctx, key, s.cfg.FrontWindowDuration).Err()
	}
	itemKey := fmt.Sprintf("news:item:%s", item.NewsID)
	if _, err := s.client.Set(ctx, itemKey, mustJSON(item), s.cfg.FrontWindowDuration).Result(); err != nil {
		return err
	}
	return nil
}

func (s *Service) flush(ctx context.Context) error {
	if len(s.buf) == 0 {
		return nil
	}
	windowEnd := time.Now()
	batch := model.BatchEnvelope{
		BatchID:      fmt.Sprintf("batch-%d", windowEnd.UnixNano()),
		CreatedAt:    windowEnd,
		ItemCount:    len(s.buf),
		WindowStart:  s.first,
		WindowEnd:    windowEnd,
		Items:        append([]model.NormalizedNewsEvent(nil), s.buf...),
		BatchType:    "normalized_news_micro_batch",
		SourceStream: s.cfg.NormalizedStream,
	}
	if _, err := redisx.AddJSON(ctx, s.client, s.cfg.BatchReadyStream, batch, 50000); err != nil {
		return err
	}
	log.Printf("aggregator: flushed batch=%s items=%d", batch.BatchID, batch.ItemCount)
	s.buf = s.buf[:0]
	s.first = time.Time{}
	return nil
}
